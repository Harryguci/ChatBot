import os
import re
import gradio as gr
import PyPDF2
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from typing import List, Dict, Tuple
import logging
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import io
import torch
from transformers import AutoModel, AutoProcessor

# Import database services
from src.config.db.services import (
    document_service, document_chunk_service, embedding_cache_service
)
from src.config.db.db_connection import get_database_connection
from src.config.db.models import Document, DocumentChunk
from src.services.base.implements.IngestionService import IngestionService
from src.services.base.implements.PdfIngestionPipeline import PdfIngestionPipeline
from src.services.base.implements.ImageIngestionPipeline import ImageIngestionPipeline

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
        """Khởi tạo chatbot với API key"""
        self.google_api_key = google_api_key
        self.setup_models()
        # >>> CHANGED: Khởi tạo các thuộc tính để lưu trữ trạng thái qua nhiều file
        self.clear_memory()
        self.load_documents_from_database() # Load documents from DB on startup
        # <<< END CHANGED

    def setup_models(self):
        """Thiết lập các model cần thiết"""
        try:
            logger.info(f"API Key được sử dụng: {self.google_api_key[:10]}..." if self.google_api_key else "API Key không tồn tại")
            genai.configure(api_key=self.google_api_key)
            
            # Use the working Gemini 2.0 Flash model
            self.llm = genai.GenerativeModel('gemini-2.0-flash-exp')
            logger.info("✓ Đã khởi tạo thành công model: gemini-2.0-flash-exp")
            
            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("Đã khởi tạo thành công các model")
            # Ingestion service + pipelines
            self.ingestion_service = IngestionService()
            self.pipelines = {
                '.pdf': PdfIngestionPipeline(self.ingestion_service),
                'image': ImageIngestionPipeline(self.ingestion_service),
            }
            # Khởi tạo Vintern Multimodal Embedding (RAG hình ảnh + văn bản)
            try:
                self.vintern_device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.vintern_dtype = torch.bfloat16 if (self.vintern_device == 'cuda' and torch.cuda.is_bf16_supported()) else torch.float32
                self.vintern_model_name = "5CD-AI/Vintern-Embedding-1B"
                self.vintern_processor = AutoProcessor.from_pretrained(self.vintern_model_name, trust_remote_code=True)
                self.vintern_model = AutoModel.from_pretrained(
                    self.vintern_model_name,
                    torch_dtype=self.vintern_dtype,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                ).eval().to(self.vintern_device)
                self.vintern_enabled = True
                logger.info("✓ Vintern multimodal embeddings đã sẵn sàng (%s, dtype=%s)", self.vintern_device, str(self.vintern_dtype))
            except Exception as vintern_err:
                self.vintern_enabled = False
                self.vintern_processor = None
                self.vintern_model = None
                logger.warning("Không thể khởi tạo Vintern embeddings: %s", str(vintern_err))
        except Exception as e:
            logger.error(f"Lỗi khởi tạo model: {str(e)}")
            raise

    # >>> CHANGED: Thêm hàm để reset "bộ nhớ" của chatbot
    def clear_memory(self):
        """Xóa tất cả tài liệu, embeddings và lịch sử file đã xử lý."""
        logger.info("Đã xóa bộ nhớ của chatbot.")
        self.documents = []
        self.embeddings = None # Sẽ là một numpy array
        self.document_metadata = []
        self.processed_files = set() # Dùng set để kiểm tra file trùng lặp hiệu quả hơn
        # Bộ nhớ đa phương thức cho Vintern
        self.vintern_doc_embeddings = []  # List[torch.Tensor]
        self.vintern_doc_metadata = []    # List[dict]
        return (
            [], # Xóa lịch sử chat
            "", # Xóa text box câu hỏi
            "Sẵn sàng xử lý file mới...", # Reset status
            "Chưa có tài liệu nào được xử lý." # Reset danh sách file
        )
    
    def load_documents_from_database(self):
        """Load all documents from database into memory on startup."""
        try:
            logger.info("Loading documents from database...")
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
                    
                    # Collect embeddings
                    if chunk.embedding:
                        embedding_array = vector_to_numpy(chunk.embedding)
                        if embedding_array is not None:
                            all_embeddings_list.append(embedding_array)
                
                # Load Vintern embeddings if available
                if getattr(self, 'vintern_enabled', False):
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
            if all_embeddings_list:
                self.embeddings = np.array(all_embeddings_list)
                logger.info(f"Loaded {len(all_documents)} chunks from {len(documents)} documents")
            else:
                logger.warning("No embeddings found in database chunks")
                
        except Exception as e:
            logger.error(f"Error loading documents from database: {str(e)}")
    # <<< END CHANGED

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Trích xuất text từ file PDF, giữ lại các dấu xuống dòng"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Đã trích xuất {len(pdf_reader.pages)} trang từ PDF")
            return text
        except Exception as e:
            logger.error(f"Lỗi đọc PDF: {str(e)}")
            raise

    def clean_text(self, text: str) -> str:
        """Làm sạch text, loại bỏ các khoảng trắng thừa nhưng giữ lại cấu trúc đoạn văn"""
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def extract_text_from_image(self, image_path: str) -> str:
        """Trích xuất text từ file hình ảnh sử dụng OCR (Tesseract)"""
        try:
            # Mở và xử lý hình ảnh
            image = Image.open(image_path)
            
            # Chuyển đổi sang RGB nếu cần
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Sử dụng Tesseract để OCR
            text = pytesseract.image_to_string(image, lang='vie+eng')
            
            logger.info(f"Đã trích xuất text từ hình ảnh: {len(text)} ký tự")
            return text
        except Exception as e:
            logger.error(f"Lỗi trích xuất text từ hình ảnh: {str(e)}")
            raise

    def extract_text_from_image_with_gemini(self, image_path: str) -> str:
        """Trích xuất text từ hình ảnh sử dụng Gemini Vision"""
        try:
            # Mở hình ảnh
            image = Image.open(image_path)
            
            # Chuyển đổi sang RGB nếu cần
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Tạo prompt cho Gemini Vision
            prompt = """
            Hãy đọc và trích xuất toàn bộ văn bản có trong hình ảnh này. 
            Bao gồm:
            1. Tất cả các tiêu đề, tiểu đề
            2. Nội dung văn bản chính
            3. Các ghi chú, chú thích
            4. Số liệu, bảng biểu (nếu có)
            
            Giữ nguyên cấu trúc và định dạng của văn bản. Trả về kết quả bằng tiếng Việt.
            """
            
            # Sử dụng Gemini để phân tích hình ảnh
            response = self.llm.generate_content([prompt, image])
            extracted_text = response.text
            
            logger.info(f"Đã trích xuất text từ hình ảnh bằng Gemini: {len(extracted_text)} ký tự")
            return extracted_text
        except Exception as e:
            logger.error(f"Lỗi trích xuất text từ hình ảnh bằng Gemini: {str(e)}")
            # Fallback to Tesseract if Gemini fails
            try:
                return self.extract_text_from_image(image_path)
            except:
                raise Exception(f"Cả hai phương pháp trích xuất đều thất bại: {str(e)}")

    def is_image_file(self, file_path: str) -> bool:
        """Kiểm tra xem file có phải là hình ảnh không"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
        file_ext = Path(file_path).suffix.lower()
        return file_ext in image_extensions

    def powerful_chunking_strategy(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
        """Chiến lược chunking mạnh mẽ kết hợp phân tích cấu trúc và chia nhỏ đệ quy."""
        logger.info("Bắt đầu chiến lược chunking nâng cao...")
        major_sections = re.split(r'\n(?=MỤC LỤC|Phần \d+|Chương \d+|[A-Z\s]{5,}\n|[IVX]+\.\s)', text)
        all_chunks = []
        current_heading = "Mở đầu"
        for section_text in major_sections:
            if not section_text.strip():
                continue
            heading_match = re.match(r'([A-Z\s]{5,}|Phần \d+.*|Chương \d+.*|[IVX]+\..*)\n', section_text)
            if heading_match:
                current_heading = heading_match.group(1).strip()
                content_text = section_text[len(heading_match.group(0)):].strip()
            else:
                content_text = section_text.strip()
            paragraphs = content_text.split('\n\n')
            current_chunk = ""
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len(current_chunk) + len(p) + 1 <= max_chunk_size:
                    current_chunk += "\n" + p
                else:
                    if current_chunk.strip():
                        all_chunks.append({"heading": current_heading, "content": current_chunk.strip()})
                    current_chunk = p
            if current_chunk.strip():
                all_chunks.append({"heading": current_heading, "content": current_chunk.strip()})
        logger.info(f"Chunking hoàn tất. Tổng số chunks: {len(all_chunks)}")
        return all_chunks

    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Tạo embeddings cho danh sách các đoạn text"""
        try:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            logger.info(f"Đã tạo embeddings cho {len(texts)} đoạn text")
            return embeddings
        except Exception as e:
            logger.error(f"Lỗi tạo embeddings: {str(e)}")
            raise

    def vintern_embed_texts(self, texts: List[str]) -> List[torch.Tensor]:
        """Create Vintern embeddings for texts."""
        try:
            if not self.vintern_enabled:
                return []
            
            batch_docs = self.vintern_processor.process_docs(texts)
            
            # Move to device
            batch_docs["input_ids"] = batch_docs["input_ids"].to(self.vintern_device)
            batch_docs["attention_mask"] = batch_docs["attention_mask"].to(self.vintern_device)
            if self.vintern_dtype != torch.float32:
                batch_docs["attention_mask"] = batch_docs["attention_mask"].to(self.vintern_dtype)
            
            with torch.no_grad():
                embeddings = self.vintern_model(**batch_docs)
            
            return list(embeddings)
        except Exception as e:
            logger.error(f"Lỗi tạo Vintern embeddings cho text: {str(e)}")
            return []

    def vintern_embed_images(self, images: List[Image.Image]) -> List[torch.Tensor]:
        """Create Vintern embeddings for images."""
        try:
            if not self.vintern_enabled:
                return []
            
            batch_images = self.vintern_processor.process_images(images)
            
            # Move to device
            batch_images["pixel_values"] = batch_images["pixel_values"].to(self.vintern_device)
            batch_images["input_ids"] = batch_images["input_ids"].to(self.vintern_device)
            batch_images["attention_mask"] = batch_images["attention_mask"].to(self.vintern_device)
            if self.vintern_dtype != torch.float32:
                batch_images["attention_mask"] = batch_images["attention_mask"].to(self.vintern_dtype)
                batch_images["pixel_values"] = batch_images["pixel_values"].to(self.vintern_dtype)
            
            with torch.no_grad():
                embeddings = self.vintern_model(**batch_images)
            
            return list(embeddings)
        except Exception as e:
            logger.error(f"Lỗi tạo Vintern embeddings cho ảnh: {str(e)}")
            return []

    # >>> CHANGED: Cập nhật hàm xử lý để dùng ingestion pipelines cho PDF & hình ảnh
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
            if getattr(self, 'vintern_enabled', False):
                try:
                    chunks = document_chunk_service.get_chunks_by_document(doc.id)
                    if chunks:
                        # Text embeddings for the chunk content
                        texts = [c.content for c in chunks]
                        vintern_text_embs = self.vintern_embed_texts(texts)
                        for idx, c in enumerate(chunks):
                            if idx < len(vintern_text_embs) and torch.is_tensor(vintern_text_embs[idx]):
                                ve = vintern_text_embs[idx].cpu().numpy().tolist()
                                document_chunk_service.update_chunk_vintern_embedding(
                                    chunk_id=c.id,
                                    vintern_embedding=ve,
                                    vintern_model=self.vintern_model_name,
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
                            img_embs = self.vintern_embed_images([img])
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

    # Giữ lại method cũ để tương thích ngược
    def process_pdf(self, pdf_path: str) -> Tuple[str, str]:
        """Wrapper method để tương thích ngược với code cũ"""
        return self.process_document(pdf_path)

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
    # <<< END CHANGED

    # >>> CHANGED: Cập nhật hàm search để trả về cả metadata
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
    # <<< END CHANGED

    # >>> NEW: Tìm kiếm đa phương thức bằng Vintern
    def search_relevant_documents_vintern(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """Tìm kiếm đa phương thức bằng Vintern; trả về (context_text, score, metadata)."""
        try:
            if not getattr(self, 'vintern_enabled', False) or not self.vintern_doc_embeddings:
                return []
            # Chuẩn bị embedding cho query
            batch = self.vintern_processor.process_queries([query])
            # Move to device/dtype
            if 'input_ids' in batch:
                batch['input_ids'] = batch['input_ids'].to(self.vintern_device)
            if 'attention_mask' in batch:
                am = batch['attention_mask'].to(self.vintern_device)
                if self.vintern_dtype != torch.float32:
                    am = am.to(self.vintern_dtype)
                batch['attention_mask'] = am
            with torch.no_grad():
                q_emb = self.vintern_model(**batch)
            scores = self.vintern_processor.score_multi_vector(q_emb, self.vintern_doc_embeddings)[0]
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
    # <<< END NEW

    # >>> CHANGED: Cập nhật hàm generate_answer để hợp nhất bằng Vintern + text
    def generate_answer(self, query: str, chat_history: List) -> Tuple[str, List, List[str]]:
        """Tạo câu trả lời dựa trên tài liệu và lịch sử chat"""
        try:
            vintern_results = self.search_relevant_documents_vintern(query, top_k=5) if getattr(self, 'vintern_enabled', False) else []
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
    # <<< END CHANGED