import os
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from typing import List, Dict, Tuple
import logging
from pathlib import Path
from PIL import Image
import torch
import asyncio
from functools import lru_cache
import hashlib
import numpy as np
# Import database services
from src.config.db.services import (
    document_service, document_chunk_service
)
from src.services.base.implements.IngestionService import IngestionService
from src.services.base.implements.PdfIngestionPipeline import PdfIngestionPipeline
from src.services.base.implements.ImageIngestionPipeline import ImageIngestionPipeline
from src.services.base.implements.BaseIngestionPipeline import BaseIngestionPipeline
from src.services.base.implements.VinternEmbeddingService import VinternEmbeddingService
# Import Redis cache
from src.config.cache import get_redis_cache

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Chatbot:
    def __init__(self, google_api_key: str):
        """Khởi tạo chatbot với API key - synchronous initialization"""
        self.google_api_key = google_api_key
        self._initialization_complete = False

        # Initialize tracking structures
        # Note: We no longer load documents/embeddings into memory.
        # All similarity searches are performed directly against the database.
        self.processed_files = set()

        # Initialize Redis cache
        self.cache = get_redis_cache()

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

        # Initialize tracking structures
        instance.processed_files = set()

        # Initialize Redis cache
        instance.cache = get_redis_cache()

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
            logger.info("Use local Vietnamese GPT-2 model: NlpHUST/gpt2-vietnamese")

            # Local Vietnamese GPT-2 text-generation pipeline
            # Uses CPU or CUDA automatically via transformers/accelerate
            # Note: This model doesn't support safetensors, so we use pytorch format
            self.llm = pipeline(
                "text-generation",
                model="NlpHUST/gpt2-vietnamese",
                model_kwargs={"use_safetensors": False},
                device_map="auto",
            )
            logger.info("✓ Successfully initialized local Vietnamese GPT-2 model: NlpHUST/gpt2-vietnamese")

            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✓ Successfully initialized embedding model")

            # Vintern Multimodal Embedding Service (RAG hình ảnh + văn bản)
            # Only initialize if not already set (for async initialization)
            if not hasattr(self, 'vintern_service') or self.vintern_service is None:
                self.vintern_service = VinternEmbeddingService()
                logger.info("✓ Successfully initialized Vintern service")
            else:
                logger.info("✓ Vintern service already initialized")

            # Ingestion service + pipelines
            self.ingestion_service = IngestionService()
            self.pipelines: Dict[str, BaseIngestionPipeline] = {
                '.pdf': PdfIngestionPipeline(self.ingestion_service),
                'image': ImageIngestionPipeline(self.ingestion_service, self.vintern_service),
            }
            logger.info("✓ Successfully initialized ingestion pipelines")
            logger.info("[setup_models] Model initialization completed")

        except Exception as e:
            logger.error(f"Error initializing models: {str(e)}")
            raise

    @lru_cache(maxsize=1000)
    def _get_cached_embedding(self, query: str) -> tuple:
        """
        Get cached embedding for a query string.
        Uses LRU cache to store up to 1000 most recent query embeddings.

        Args:
            query: Query string

        Returns:
            Tuple of embedding values (hashable for caching)
        """
        embedding = self.embedding_model.encode([query])[0]
        # Convert numpy array to tuple for hashability
        return tuple(embedding.tolist())

    def get_query_embedding(self, query: str) -> np.ndarray:
        """
        Get query embedding with LRU caching.

        Args:
            query: Query string

        Returns:
            Numpy array of embedding
        """
        cached_tuple = self._get_cached_embedding(query)
        return np.array(cached_tuple)

    def load_documents_from_database(self):
        """
        Load document metadata from database on startup.

        Note: Embeddings are no longer loaded into memory. Instead, similarity searches
        are performed directly against the database using the new recency-weighted queries.
        """
        try:
            logger.info("[load_documents_from_database] Loading document metadata from database...")
            documents = document_service.get_all_processed_documents()

            if not documents:
                logger.info("No documents found in database.")
                return

            # Only load filenames into processed_files for tracking
            for doc in documents:
                self.processed_files.add(doc.filename)
                logger.debug(f"Registered document: {doc.filename} (ID: {doc.id})")

            logger.info(f"✓ Loaded metadata for {len(documents)} documents")
            logger.info("[load_documents_from_database] Document metadata loading completed")

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
            # All embeddings are saved to database - no in-memory caching
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
                                logger.debug(f"Saved Vintern embedding for chunk {c.id}")

                    # For images, add image embedding entry to database
                    if is_image:
                        try:
                            img = Image.open(pipeline_path)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img_embs = self.vintern_service.embed_images([img])
                            if img_embs and chunks:
                                # Store image embedding in the first chunk
                                ve = img_embs[0].cpu().numpy().tolist()
                                document_chunk_service.update_chunk_vintern_embedding(
                                    chunk_id=chunks[0].id,
                                    vintern_embedding=ve,
                                    vintern_model=self.vintern_service.get_model_name(),
                                )
                                logger.debug(f"Saved Vintern image embedding for chunk {chunks[0].id}")
                        except Exception as img_e:
                            logger.warning("Không thể tạo Vintern embedding cho ảnh: %s", str(img_e))
                except Exception as vintern_e:
                    logger.warning("Không thể cập nhật Vintern embeddings: %s", str(vintern_e))

            if loaded_after > 0:
                self.processed_files.add(desired_filename)

            # Get total chunks from database
            all_documents = document_service.get_all_processed_documents()
            total_chunks = sum(len(document_chunk_service.get_chunks_by_document(d.id)) for d in all_documents)

            # Invalidate query cache since new documents were added
            self.cache.invalidate_query_cache()
            logger.info("Query cache invalidated after document upload")

            status_message = (
                f"Xử lý thành công '{desired_filename}' ({file_type})!\n"
                f"- Số chunks mới: {len(document_chunk_service.get_chunks_by_document(doc.id))}\n"
                f"- Tổng số chunks trong database: {total_chunks:,}"
            )
            return status_message, self._get_processed_files_markdown()

        except Exception as e:
            error_msg = f"Lỗi xử lý tài liệu: {str(e)}"
            logger.error(error_msg)
            return error_msg, self._get_processed_files_markdown()

    def _load_document_into_memory(self, document_id: int, filename: str, file_type: str) -> int:
        """
        Register a document in the processed files tracker.

        Note: This method no longer loads chunks or embeddings into memory.
        Similarity searches are performed directly against the database.

        Returns the number of chunks in the document.
        """
        chunks = document_chunk_service.get_chunks_by_document(document_id)
        if not chunks:
            logger.warning("No chunks found when loading document '%s'", filename)
            return 0

        # Just track that we've processed this file
        self.processed_files.add(filename)
        logger.info(f"Registered document '{filename}' with {len(chunks)} chunks")

        return len(chunks)

    def _find_filename_for_chunk(self, chunk_id: int) -> str:
        """Best-effort resolve filename for a given chunk id from database."""
        try:
            chunk = document_chunk_service.get_chunk_by_id(chunk_id)
            if chunk:
                doc = document_service.get_document_by_id(chunk.document_id)
                if doc:
                    return doc.filename
        except Exception as e:
            logger.warning(f"Error finding filename for chunk {chunk_id}: {str(e)}")
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
        """Delete a document from database and tracking."""
        try:
            # Check if document exists in database
            doc = document_service.get_document_by_filename(filename)

            if not doc:
                return False, f"Document '{filename}' not found in database."

            # Delete from database (cascades to chunks and embeddings)
            deleted = document_service.delete_document_by_filename(filename)
            if not deleted:
                return False, f"Failed to delete document '{filename}' from database."

            # Remove from processed_files tracker
            self.processed_files.discard(filename)

            # Invalidate query cache since documents were deleted
            self.cache.invalidate_query_cache()
            logger.info(f"Query cache invalidated after document deletion")

            logger.info(f"Deleted document '{filename}' from database")
            return True, f"Đã xóa tài liệu '{filename}' từ database."

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

    def search_relevant_documents(self, query: str, top_k: int = 5, recency_weight: float = 0.15) -> List[Tuple[str, float, dict]]:
        """
        Tìm kiếm các đoạn văn liên quan trực tiếp từ database với recency boost.

        Args:
            query: Câu truy vấn
            top_k: Số lượng kết quả tối đa
            recency_weight: Trọng số cho độ mới của embeddings (0-1), mặc định 0.15

        Returns:
            List of tuples (content, similarity_score, metadata)
        """
        try:
            # Try to get cached results
            cached_results = self.cache.get_query_results(query, top_k=top_k, search_type="text")
            if cached_results is not None:
                logger.info(f"Cache HIT for text search: {query[:50]}...")
                # Convert from dict format back to tuple format
                return [(r['content'], r['score'], r['metadata']) for r in cached_results]

            # Cache miss - perform database search
            logger.debug(f"Cache MISS for text search: {query[:50]}...")

            # Generate query embedding with LRU cache
            query_embedding = self.get_query_embedding(query)

            # Use database service with recency boost
            chunks_with_scores = document_chunk_service.find_similar_chunks_by_embedding(
                query_embedding=query_embedding.tolist(),
                limit=top_k,
                threshold=0.0,  # We'll filter later if needed
                recency_weight=recency_weight
            )

            # Convert to expected format
            results = []
            for chunk, score in chunks_with_scores:
                # Get document info
                doc = document_service.get_document_by_id(chunk.document_id)

                metadata = {
                    'chunk_id': chunk.id,
                    'source_file': doc.filename if doc else 'unknown',
                    'file_type': doc.file_type if doc else 'unknown',
                    'heading': chunk.heading or '',
                    'length': len(chunk.content),
                    'preview': chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content,
                    'created_at': str(chunk.created_at) if chunk.created_at else None
                }

                results.append((chunk.content, score, metadata))

            # Cache results for future queries
            cache_data = [
                {'content': content, 'score': score, 'metadata': metadata}
                for content, score, metadata in results
            ]
            self.cache.set_query_results(query, cache_data, top_k=top_k, search_type="text", ttl=3600)

            return results

        except Exception as e:
            logger.error(f"Lỗi tìm kiếm: {str(e)}")
            return []

    def search_relevant_documents_vintern(self, query: str, top_k: int = 5, recency_weight: float = 0.15) -> List[Tuple[str, float, dict]]:
        """
        Tìm kiếm đa phương thức bằng Vintern trực tiếp từ database với recency boost.

        Args:
            query: Câu truy vấn
            top_k: Số lượng kết quả tối đa
            recency_weight: Trọng số cho độ mới của embeddings (0-1), mặc định 0.15

        Returns:
            List of tuples (content, similarity_score, metadata)
        """
        try:
            if not self.vintern_service.is_enabled():
                return []

            # Try to get cached results
            cached_results = self.cache.get_query_results(query, top_k=top_k, search_type="vintern")
            if cached_results is not None:
                logger.info(f"Cache HIT for Vintern search: {query[:50]}...")
                # Convert from dict format back to tuple format
                return [(r['content'], r['score'], r['metadata']) for r in cached_results]

            # Cache miss - perform database search
            logger.debug(f"Cache MISS for Vintern search: {query[:50]}...")

            # Chuẩn bị embedding cho query
            q_emb = self.vintern_service.process_query(query)
            if q_emb is None:
                return []

            # Convert tensor to list for database query
            if isinstance(q_emb, torch.Tensor):
                query_embedding = q_emb.cpu().numpy().tolist()
            else:
                query_embedding = q_emb

            # Use database service with recency boost
            chunks_with_scores = document_chunk_service.find_similar_chunks_by_vintern_embedding(
                query_embedding=query_embedding,
                limit=top_k,
                threshold=0.0,  # We'll filter later if needed
                recency_weight=recency_weight
            )

            # Convert to expected format
            results: List[Tuple[str, float, dict]] = []
            for chunk, score in chunks_with_scores:
                # Get document info
                doc = document_service.get_document_by_id(chunk.document_id)

                context_text = chunk.content or f"[Tài liệu {doc.file_type if doc else 'unknown'} từ file {doc.filename if doc else '?'}]"

                metadata = {
                    'type': 'text',
                    'source_file': doc.filename if doc else 'unknown',
                    'file_type': doc.file_type if doc else 'unknown',
                    'heading': chunk.heading or '',
                    'content': chunk.content,
                    'preview': chunk.content[:150] + "..." if chunk.content and len(chunk.content) > 150 else chunk.content,
                    'created_at': str(chunk.created_at) if chunk.created_at else None
                }

                results.append((context_text, score, metadata))

            # Cache results for future queries
            cache_data = [
                {'content': content, 'score': score, 'metadata': metadata}
                for content, score, metadata in results
            ]
            self.cache.set_query_results(query, cache_data, top_k=top_k, search_type="vintern", ttl=3600)

            return results

        except Exception as e:
            logger.error(f"Lỗi tìm kiếm Vintern: {str(e)}")
            return []

    def generate_answer(self, query: str, chat_history: List) -> Tuple[str, List, List[str]]:
        """Tạo câu trả lời dựa trên tài liệu và lịch sử chat"""
        try:
            # Search using database-backed queries with recency boost
            vintern_results = self.search_relevant_documents_vintern(query, top_k=5, recency_weight=0.15) if self.vintern_service.is_enabled() else []
            text_results = self.search_relevant_documents(query, top_k=5, recency_weight=0.15)

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

            gen_outputs = self.llm(
                prompt,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.8,
                top_p=0.95,
                pad_token_id=self.llm.tokenizer.eos_token_id if hasattr(self.llm, "tokenizer") and self.llm.tokenizer.eos_token_id is not None else None,
            )
            answer = gen_outputs[0]["generated_text"]

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