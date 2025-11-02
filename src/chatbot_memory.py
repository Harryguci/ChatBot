import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoModel, AutoProcessor
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import database services
from src.config.db.services import (
    document_service, document_chunk_service, embedding_cache_service
)
from src.config.db.db_connection import get_database_connection
from src.config.db.models import Document, DocumentChunk
from src.services.base.implements.IngestionService import IngestionService
from src.services.base.implements.PdfIngestionPipeline import PdfIngestionPipeline
from src.services.base.implements.ImageIngestionPipeline import ImageIngestionPipeline
from src.services.base.implements.BaseIngestionPipeline import BaseIngestionPipeline
from src.services.base.implements.VinternEmbeddingService import VinternEmbeddingService

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def vector_to_numpy(embedding) -> np.ndarray:
    """
    Convert pgvector Vector type to numpy array.
    
    Args:
        embedding: Vector embedding from database (pgvector type)
        
    Returns:
        numpy array of the embedding
    """
    if embedding is None:
        return None
    if isinstance(embedding, np.ndarray):
        return embedding
    if isinstance(embedding, list):
        return np.array(embedding, dtype=np.float32)
    # For pgvector Vector type, it should be convertible directly
    try:
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        logger.warning(f"Error converting embedding to numpy: {str(e)}")
        return None

class Chatbot:
    def __init__(self, google_api_key: str):
        """Khởi tạo chatbot với API key - synchronous initialization"""
        self.google_api_key = google_api_key
        self._initialization_complete = False

        # Initialize memory structures first
        self.documents = []
        self.embeddings = None
        self.document_metadata = []
        self.processed_files = set()
        self.vintern_doc_embeddings: List[torch.Tensor] = []
        self.vintern_doc_metadata: List[Dict] = []

        # Run synchronous initialization
        self.setup_models()
        self.load_documents_from_database()
        self._initialization_complete = True

    @classmethod
    async def create_async(cls, google_api_key: str) -> 'Chatbot':
        """
        Factory method for async initialization with concurrent model setup and document loading.

        Usage:
            chatbot = await Chatbot.create_async(api_key)
        """
        logger.info("Starting async chatbot initialization...")

        # Create instance without full initialization
        instance = cls.__new__(cls)
        instance.google_api_key = google_api_key
        instance._initialization_complete = False

        # Initialize memory structures
        instance.documents = []
        instance.embeddings = None
        instance.document_metadata = []
        instance.processed_files = set()
        instance.vintern_doc_embeddings = []
        instance.vintern_doc_metadata = []

        # Initialize VinternEmbeddingService BEFORE concurrent tasks
        # This is needed because load_documents_from_database() may access it
        from src.services.base.implements.VinternEmbeddingService import VinternEmbeddingService
        instance.vintern_service = VinternEmbeddingService()
        logger.info("✓ Vintern service pre-initialized for async loading")

        # Run setup_models and load_documents_from_database concurrently
        try:
            setup_task = asyncio.create_task(
                asyncio.to_thread(instance.setup_models)
            )
            load_task = asyncio.create_task(
                asyncio.to_thread(instance.load_documents_from_database)
            )

            # Wait for both tasks to complete
            await asyncio.gather(setup_task, load_task)

            instance._initialization_complete = True
            logger.info("✓ Async chatbot initialization completed successfully")

            return instance

        except Exception as e:
            logger.error(f"Error during async initialization: {str(e)}")
            raise

    def setup_models(self):
        """Thiết lập các model cần thiết"""
        try:
            logger.info(f"[setup_models] Starting model initialization...")
            logger.info(f"API Key được sử dụng: {self.google_api_key[:10]}..." if self.google_api_key else "API Key không tồn tại")
            genai.configure(api_key=self.google_api_key)

            # Use the working Gemini 2.0 Flash model
            self.llm = genai.GenerativeModel('gemini-2.0-flash-exp')
            logger.info("✓ Đã khởi tạo thành công model: gemini-2.0-flash-exp")

            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✓ Đã khởi tạo thành công embedding model")

            # Vintern Multimodal Embedding Service (RAG hình ảnh + văn bản)
            # Only initialize if not already set (for async initialization)
            if not hasattr(self, 'vintern_service') or self.vintern_service is None:
                self.vintern_service = VinternEmbeddingService()
                logger.info("✓ Đã khởi tạo Vintern service")
            else:
                logger.info("✓ Vintern service already initialized")

            # Ingestion service + pipelines
            self.ingestion_service = IngestionService()
            self.pipelines: Dict[str, BaseIngestionPipeline] = {
                '.pdf': PdfIngestionPipeline(self.ingestion_service),
                'image': ImageIngestionPipeline(self.ingestion_service, self.vintern_service),
            }
            logger.info("✓ Đã khởi tạo ingestion pipelines")
            logger.info("[setup_models] Model initialization completed")

        except Exception as e:
            logger.error(f"Lỗi khởi tạo model: {str(e)}")
            raise

    def clear_memory(self):
        """Xóa tất cả tài liệu, embeddings và lịch sử file đã xử lý."""
        logger.info("Đã xóa bộ nhớ của chatbot.")
        self.documents = []
        self.embeddings = None # Sẽ là một numpy array
        self.document_metadata = []
        self.processed_files = set() # Dùng set để kiểm tra file trùng lặp hiệu quả hơn
        # Bộ nhớ đa phương thức cho Vintern
        self.vintern_doc_embeddings: List[torch.Tensor] = []
        self.vintern_doc_metadata: List[Dict] = []
        return (
            [], # Xóa lịch sử chat
            "", # Xóa text box câu hỏi
            "Sẵn sàng xử lý file mới...", # Reset status
            "Chưa có tài liệu nào được xử lý." # Reset danh sách file
        )
    
    def load_documents_from_database(self):
        """Load all documents from database into memory on startup."""
        try:
            logger.info("[load_documents_from_database] Starting document loading from database...")
            documents = document_service.get_all_processed_documents()
            
            if not documents:
                logger.info("No documents found in database.")
                return
            
            all_embeddings_list = []
            all_documents = []
            all_metadata = []
            
            for doc in documents:
                logger.info(f"Loading document: {doc.filename} (ID: {doc.id})")
                
                # Get chunks for this document
                chunks = document_chunk_service.get_chunks_by_document(doc.id)
                
                if not chunks:
                    logger.warning(f"No chunks found for document {doc.filename}")
                    continue
                
                # Add filename to processed_files
                self.processed_files.add(doc.filename)
                
                # Load chunks into memory
                for chunk in chunks:
                    all_documents.append(chunk.content)
                    all_metadata.append({
                        'chunk_id': chunk.id,
                        'source_file': doc.filename,
                        'file_type': doc.file_type,
                        'heading': chunk.heading or '',
                        'length': len(chunk.content),
                        'preview': chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
                    })

                    # Collect embeddings with detailed logging
                    if chunk.embedding is not None:
                        logger.debug(f"  Chunk {chunk.id}: embedding exists, type={type(chunk.embedding).__name__}")
                        try:
                            embedding_array = vector_to_numpy(chunk.embedding)
                            if embedding_array is not None:
                                all_embeddings_list.append(embedding_array)
                                logger.debug(f"    ✓ Converted to numpy: shape={embedding_array.shape}")
                            else:
                                logger.warning(f"    ✗ vector_to_numpy returned None for chunk {chunk.id}")
                        except Exception as e:
                            logger.error(f"    ✗ Error converting embedding for chunk {chunk.id}: {str(e)}")
                    else:
                        logger.warning(f"  Chunk {chunk.id}: No embedding found")
                
                # Load Vintern embeddings if available
                if self.vintern_service.is_enabled():
                    try:
                        for chunk in chunks:
                            if chunk.vintern_embedding:
                                # Convert Vector to numpy array and then to tensor
                                vintern_array = vector_to_numpy(chunk.vintern_embedding)
                                if vintern_array is not None:
                                    vintern_tensor = torch.tensor(vintern_array, dtype=torch.float32)
                                    self.vintern_doc_embeddings.append(vintern_tensor)
                                    self.vintern_doc_metadata.append({
                                        'type': 'text',
                                        'source_file': doc.filename,
                                        'file_type': doc.file_type,
                                        'heading': chunk.heading or '',
                                        'content': chunk.content,
                                        'preview': chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content,
                                    })
                    except Exception as e:
                        logger.warning(f"Error loading Vintern embeddings from database: {str(e)}")
            
            # Set documents and metadata
            self.documents = all_documents
            self.document_metadata = all_metadata
            
            # Rebuild embeddings array
            logger.info(f"Collected {len(all_embeddings_list)} embeddings from {len(all_documents)} chunks")

            if all_embeddings_list:
                self.embeddings = np.array(all_embeddings_list)
                logger.info(f"✓ Loaded {len(all_documents)} chunks from {len(documents)} documents")
                logger.info(f"✓ Embeddings matrix shape: {self.embeddings.shape}")
            else:
                logger.warning("⚠ No embeddings found in database chunks - Chatbot.embeddings will be None")
                logger.warning("  This means text-based search will not work!")
                logger.warning("  Possible causes:")
                logger.warning("    1. Documents were processed without generating embeddings")
                logger.warning("    2. Database migration issue")
                logger.warning("    3. Embeddings were not saved properly")

            logger.info("[load_documents_from_database] Document loading completed")

        except Exception as e:
            logger.error(f"Error loading documents from database: {str(e)}")

    def is_image_file(self, file_path: str) -> bool:
        """Kiểm tra xem file có phải là hình ảnh không"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        file_ext = Path(file_path).suffix.lower()
        return file_ext in image_extensions

    def process_document(self, file_path: str, original_filename: str = None) -> Tuple[str, str]:
        """Xử lý tài liệu bằng ingestion pipelines và nạp vào bộ nhớ từ DB."""
        try:
            if not file_path:
                return "Vui lòng chọn một file PDF hoặc hình ảnh.", self._get_processed_files_markdown()

            # Chuẩn hóa tên file sẽ lưu trong DB: ưu tiên tên gốc nếu có
            desired_filename = original_filename if original_filename else Path(file_path).name
            if desired_filename in self.processed_files:
                logger.warning("Tệp '%s' đã được xử lý trước đó. Bỏ qua.", desired_filename)
                return f"Tệp '{desired_filename}' đã được xử lý. Sẵn sàng nhận câu hỏi.", self._get_processed_files_markdown()

            # Nếu tài liệu đã tồn tại trong DB, chỉ cần nạp vào bộ nhớ
            existing_doc = document_service.check_document_exists_by_filename(desired_filename, desired_filename)
            if existing_doc:
                # If the document exists but has no chunks, continue to process to create chunks
                existing_chunks = document_chunk_service.get_chunks_by_document(existing_doc.id)
                if existing_chunks:
                    logger.info("Document '%s' already exists in database with %d chunk(s)", desired_filename, len(existing_chunks))
                    loaded = self._load_document_into_memory(existing_doc.id, desired_filename, existing_doc.file_type)
                    if loaded > 0:
                        self.processed_files.add(desired_filename)
                        return f"Document '{desired_filename}' loaded from database.", self._get_processed_files_markdown()
                    else:
                        logger.warning("Document '%s' reported chunks but none loaded; proceeding to re-process.", desired_filename)
                else:
                    logger.info("Document '%s' exists but has no chunks. Proceeding to process and create chunks.", desired_filename)

            # Chọn pipeline theo loại file
            ext = Path(desired_filename).suffix.lower()
            is_image = self.is_image_file(desired_filename)
            pipeline = self.pipelines['image'] if is_image else self.pipelines.get(ext)
            if pipeline is None:
                return (
                    "Định dạng file không được hỗ trợ. Chỉ hỗ trợ PDF và các định dạng hình ảnh (JPG, PNG, BMP, GIF, TIFF, WEBP).",
                    self._get_processed_files_markdown(),
                )

            # Đảm bảo pipeline lưu đúng tên file: tạo bản sao tạm với tên gốc
            temp_dir = Path(file_path).parent
            temp_target = temp_dir / desired_filename
            if Path(file_path) != temp_target:
                try:
                    # Copy bytes to new temp path with desired filename
                    with open(file_path, 'rb') as src, open(temp_target, 'wb') as dst:
                        dst.write(src.read())
                    pipeline_path = str(temp_target)
                except Exception:
                    # Fallback: dùng đường dẫn gốc nếu copy thất bại
                    pipeline_path = file_path
            else:
                pipeline_path = file_path

            # Gọi pipeline: Extract -> Embed -> Store (tạo document + 1 chunk)
            result = pipeline.process(pipeline_path)
            file_type = 'IMAGE' if is_image else 'PDF'

            # Nạp lại tài liệu từ DB vào bộ nhớ cho truy vấn
            # Ưu tiên lấy theo filename mong muốn
            doc = document_service.check_document_exists_by_filename(desired_filename, desired_filename) or existing_doc
            if not doc:
                # As a fallback, try to find by whatever filename was persisted
                persisted_name = result.get('filename') if isinstance(result, dict) else None
                if persisted_name:
                    doc = document_service.get_document_by_filename(persisted_name)
                    desired_filename = persisted_name
            if not doc:
                raise RuntimeError("Không tìm thấy document vừa lưu trong cơ sở dữ liệu")

            loaded_after = self._load_document_into_memory(doc.id, desired_filename, file_type)

            # Vintern: bổ sung embedding nếu khả dụng cho text (single chunk) và ảnh
            if self.vintern_service.is_enabled():
                try:
                    chunks = document_chunk_service.get_chunks_by_document(doc.id)
                    if chunks:
                        # Text embeddings for the chunk content
                        texts = [c.content for c in chunks]
                        vintern_text_embs = self.vintern_service.embed_texts(texts)
                        for idx, c in enumerate(chunks):
                            if idx < len(vintern_text_embs) and torch.is_tensor(vintern_text_embs[idx]):
                                ve = vintern_text_embs[idx].cpu().numpy().tolist()
                                document_chunk_service.update_chunk_vintern_embedding(
                                    chunk_id=c.id,
                                    vintern_embedding=ve,
                                    vintern_model=self.vintern_service.get_model_name(),
                                )
                                # update in-memory caches too
                                self.vintern_doc_embeddings.append(vintern_text_embs[idx])
                                self.vintern_doc_metadata.append({
                                    'type': 'text',
                                    'source_file': desired_filename,
                                    'file_type': file_type,
                                    'heading': c.heading or '',
                                    'content': c.content,
                                    'preview': c.content[:150] + "..." if len(c.content) > 150 else c.content,
                                })

                    # For images, add image embedding entry
                    if is_image:
                        try:
                            img = Image.open(pipeline_path)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img_embs = self.vintern_service.embed_images([img])
                            if img_embs:
                                self.vintern_doc_embeddings.append(img_embs[0])
                                # Use the first chunk (or nothing) for preview content
                                preview_text = chunks[0].content if chunks else ''
                                self.vintern_doc_metadata.append({
                                    'type': 'image',
                                    'source_file': desired_filename,
                                    'file_type': file_type,
                                    'heading': 'Hình ảnh',
                                    'content': preview_text,
                                    'preview': (preview_text[:150] + '...') if preview_text else 'Ảnh không có OCR',
                                })
                        except Exception as img_e:
                            logger.warning("Không thể tạo Vintern embedding cho ảnh: %s", str(img_e))
                except Exception as vintern_e:
                    logger.warning("Không thể cập nhật Vintern embeddings: %s", str(vintern_e))

            if loaded_after > 0:
                self.processed_files.add(desired_filename)

            total_chunks = len(self.documents)
            status_message = (
                f"Xử lý thành công '{desired_filename}' ({file_type})!\n"
                f"- Số chunks mới: {len(document_chunk_service.get_chunks_by_document(doc.id))}\n"
                f"- Tổng số chunks trong bộ nhớ: {total_chunks:,}"
            )
            return status_message, self._get_processed_files_markdown()

        except Exception as e:
            error_msg = f"Lỗi xử lý tài liệu: {str(e)}"
            logger.error(error_msg)
            return error_msg, self._get_processed_files_markdown()

    def _load_document_into_memory(self, document_id: int, filename: str, file_type: str) -> int:
        """Load a document's chunks + embeddings from DB into in-memory caches.
        Returns the number of chunks loaded."""
        chunks = document_chunk_service.get_chunks_by_document(document_id)
        if not chunks:
            logger.warning("No chunks found when loading document '%s'", filename)
            return 0

        # Append documents and metadata
        for chunk in chunks:
            self.documents.append(chunk.content)
            self.document_metadata.append({
                'chunk_id': chunk.id,
                'source_file': filename,
                'file_type': file_type,
                'heading': chunk.heading or '',
                'length': len(chunk.content),
                'preview': chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content,
            })

        # Rebuild/append embeddings matrix
        embeddings_list = [vector_to_numpy(chunk.embedding) for chunk in chunks if chunk.embedding]
        embeddings_list = [emb for emb in embeddings_list if emb is not None]
        if embeddings_list:
            if self.embeddings is not None:
                self.embeddings = np.vstack([self.embeddings, np.array(embeddings_list)])
            else:
                self.embeddings = np.array(embeddings_list)
        return len(chunks)

    def _find_filename_for_chunk(self, chunk_id: int) -> str:
        """Best-effort resolve filename for a given chunk id from in-memory metadata."""
        for meta in self.document_metadata:
            if meta.get('chunk_id') == chunk_id:
                return meta.get('source_file') or 'unknown'
        return 'unknown'

    def _get_processed_files_markdown(self) -> str:
        """Tạo chuỗi markdown hiển thị danh sách các file đã xử lý."""
        if not self.processed_files:
            return "Chưa có tài liệu nào được xử lý."
        
        md_string = "**Các tài liệu trong bộ nhớ:**\n"
        for i, file_name in enumerate(self.processed_files, 1):
            md_string += f"{i}. {file_name}\n"
        return md_string
    
    def delete_document(self, filename: str) -> Tuple[bool, str]:
        """Delete a document from database and memory."""
        try:
            # Check if document exists in database
            doc = document_service.get_document_by_filename(filename)
            db_exists = doc is not None
            memory_exists = filename in self.processed_files
            
            if not db_exists and not memory_exists:
                return False, f"Document '{filename}' not found in database or memory."
            
            # Delete from database if it exists there
            db_deleted = False
            if db_exists:
                deleted = document_service.delete_document_by_filename(filename)
                if not deleted:
                    return False, f"Failed to delete document '{filename}' from database."
                db_deleted = True
                logger.info(f"Deleted document '{filename}' from database")
            else:
                logger.warning(f"Document '{filename}' exists only in memory, not in database")
            
            # Delete from memory cache
            indices_to_remove = []
            for idx, metadata in enumerate(self.document_metadata):
                if metadata.get('source_file') == filename:
                    indices_to_remove.append(idx)
            
            # Delete in reverse order to maintain indices
            for idx in reversed(indices_to_remove):
                del self.document_metadata[idx]
                del self.documents[idx]
                
                # Delete corresponding embedding
                if self.embeddings is not None and len(self.embeddings) > idx:
                    self.embeddings = np.delete(self.embeddings, idx, axis=0)
            
            # Delete Vintern embeddings
            vintern_indices_to_remove = []
            for idx, metadata in enumerate(self.vintern_doc_metadata):
                if metadata.get('source_file') == filename:
                    vintern_indices_to_remove.append(idx)
            
            for idx in reversed(vintern_indices_to_remove):
                del self.vintern_doc_metadata[idx]
                if idx < len(self.vintern_doc_embeddings):
                    del self.vintern_doc_embeddings[idx]
            
            # Remove from processed_files
            self.processed_files.discard(filename)
            
            if db_deleted:
                logger.info(f"Đã xóa tài liệu '{filename}' từ database và bộ nhớ. Số chunks còn lại: {len(self.documents)}")
                return True, f"Đã xóa tài liệu '{filename}' từ database và bộ nhớ."
            else:
                logger.info(f"Đã xóa tài liệu '{filename}' từ bộ nhớ (không tồn tại trong database). Số chunks còn lại: {len(self.documents)}")
                return True, f"Đã xóa tài liệu '{filename}' từ bộ nhớ."
            
        except Exception as e:
            error_msg = f"Lỗi khi xóa tài liệu: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_documents_list(self) -> List[Dict]:
        """Trả về danh sách tài liệu đã xử lý với thông tin chi tiết từ database."""
        try:
            documents_info = []
            
            # Get all documents from database as dictionaries to avoid session issues
            documents = document_service.get_all_documents_dict()
            
            for doc in documents:
                doc_id = doc['id']
                
                # Get chunks for this document
                chunks = document_chunk_service.get_chunks_by_document(doc_id)
                
                # Get the first chunk for preview
                heading = 'N/A'
                preview = ''
                if chunks:
                    heading = chunks[0].heading or 'N/A'
                    content_preview = chunks[0].content
                    preview = content_preview[:150] + "..." if len(content_preview) > 150 else content_preview
                
                documents_info.append({
                    'filename': doc['filename'],
                    'file_type': doc['file_type'],
                    'chunks_count': len(chunks),
                    'heading': heading,
                    'preview': preview,
                    'file_size': doc['file_size'],
                    'created_at': doc['created_at'].isoformat() if doc['created_at'] else None,
                    'status': doc['processing_status']
                })
            
            return documents_info
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách tài liệu từ database: {str(e)}")
            return []

    def search_relevant_documents(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """Tìm kiếm các đoạn văn liên quan, trả về cả metadata."""
        try:
            if self.embeddings is None or len(self.documents) == 0:
                return []

            query_embedding = self.embedding_model.encode([query])
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = [
                (self.documents[idx], similarities[idx], self.document_metadata[idx])
                for idx in top_indices
            ]
            return results
        except Exception as e:
            logger.error(f"Lỗi tìm kiếm: {str(e)}")
            return []

    def search_relevant_documents_vintern(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """Tìm kiếm đa phương thức bằng Vintern; trả về (context_text, score, metadata)."""
        try:
            if not self.vintern_service.is_enabled() or not self.vintern_doc_embeddings:
                return []

            # Chuẩn bị embedding cho query
            q_emb = self.vintern_service.process_query(query)
            if q_emb is None:
                return []

            # Score documents against query
            scores = self.vintern_service.score_multi_vector(q_emb, self.vintern_doc_embeddings)
            if scores is None:
                return []

            top_indices = scores.argsort(descending=True)[:top_k]

            results: List[Tuple[str, float, dict]] = []
            for idx in top_indices.tolist():
                meta = self.vintern_doc_metadata[idx]
                score = float(scores[idx].item())
                context_text = meta.get('content', '') or f"[Tài liệu {meta.get('type','unknown')} từ file {meta.get('source_file','?')}]"
                results.append((context_text, score, meta))
            return results
        except Exception as e:
            logger.error(f"Lỗi tìm kiếm Vintern: {str(e)}")
            return []

    def generate_answer(self, query: str, chat_history: List) -> Tuple[str, List, List[str]]:
        """Tạo câu trả lời dựa trên tài liệu và lịch sử chat"""
        try:
            vintern_results = self.search_relevant_documents_vintern(query, top_k=5) if self.vintern_service.is_enabled() else []
            text_results = self.search_relevant_documents(query, top_k=5) if self.documents else []

            combined = vintern_results + text_results
            combined.sort(key=lambda x: x[1], reverse=True)

            # Lower threshold to be more permissive if embeddings are sparse/zero
            min_threshold = 0.1

            # Fallback: keyword search in DB when vector results are too weak
            if not combined or combined[0][1] < min_threshold:
                try:
                    chunks = document_chunk_service.search_chunks_by_content(query, limit=5)
                    if chunks:
                        combined = []
                        for c in chunks:
                            combined.append((c.content, 0.15, {  # assign a small confidence
                                'source_file': self._find_filename_for_chunk(c.id) or 'unknown',
                                'file_type': 'PDF',
                            }))
                    else:
                        error_msg = "Tôi không tìm thấy thông tin đủ liên quan trong các tài liệu đã cung cấp để trả lời câu hỏi này."
                        chat_history.append((query, error_msg))
                        return "", chat_history, []
                except Exception:
                    error_msg = "Tôi không tìm thấy thông tin đủ liên quan trong các tài liệu đã cung cấp để trả lời câu hỏi này."
                    chat_history.append((query, error_msg))
                    return "", chat_history, []

            top_k = min(5, len(combined))
            selected = combined[:top_k]

            context = ""
            source_files = []
            # Only include files from the top 2 most relevant results
            top_results_for_sources = min(1, len(selected))
            for i, (doc, score, metadata) in enumerate(selected, 1):
                file_type = metadata.get('file_type', metadata.get('type', 'Tài liệu'))
                source_file = metadata.get('source_file', '?')
                context += f"\n--- (Từ file: '{source_file}' ({file_type}), Độ liên quan: {score:.2f}) ---\n{doc}\n"
                # Only add files from the top results (most relevant)
                if i <= top_results_for_sources and source_file not in source_files:
                    source_files.append(source_file)

            prompt = f"""
            Bạn là một trợ lý AI chuyên nghiệp, trả lời câu hỏi dựa trên các trích dẫn từ các tài liệu được cung cấp.

            HƯỚNG DẪN BẮT BUỘC:
            1.  **CHỈ DÙNG THÔNG TIN CÓ SẴN:** Chỉ trả lời dựa vào nội dung trong các "Trích dẫn" dưới đây. Không tự bịa đặt hoặc dùng kiến thức bên ngoài.
            2.  **TRÍCH DẪN NGUỒN:** Khi trả lời, hãy đề cập đến thông tin được lấy từ file nào nếu có thể.
            3.  **TỔNG HỢP THÔNG TIN:** Tổng hợp thông tin từ các trích dẫn để đưa ra câu trả lời đầy đủ, chính xác và mạch lạc cho câu hỏi.
            4.  **NẾU KHÔNG CÓ THÔNG TIN:** Nếu các trích dẫn không chứa thông tin để trả lời câu hỏi, hãy nói rõ: "Dựa trên các thông tin được cung cấp, tôi không tìm thấy câu trả lời cho câu hỏi này."

            --- BỐI CẢNH TỪ TÀI LIỆU ---
            {context}
            
            --- CÂU HỎI CỦA NGƯỜI DÙNG ---
            {query}
            
            --- CÂU TRẢ LỜI CÔ ĐỌNG VÀ CHÍNH XÁC ---
            """

            response = self.llm.generate_content(prompt)
            answer = response.text

            confidence_score = combined[0][1]
            confidence_info = f"<br/><br/>---<br/><span style='color: #FF6B6B;'>*Độ tin cậy của nguồn chính: {confidence_score:.2%}*</span>"
            if confidence_score < 0.4:
                confidence_info += " (Thấp - Câu trả lời có thể không liên quan chặt chẽ)"
            elif confidence_score < 0.65:
                confidence_info += " (Trung bình)"
            else:
                confidence_info += " (Cao)"

            final_answer = '<p>' + answer + confidence_info + '</p>'
            chat_history.append((query, final_answer))
            return "", chat_history, source_files

        except Exception as e:
            error_msg = f"Lỗi tạo câu trả lời: {str(e)}"
            logger.error(error_msg)
            chat_history.append((query, error_msg))
            return "", chat_history, []