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

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFChatbot:
    def __init__(self, google_api_key: str):
        """Khởi tạo chatbot với API key"""
        self.google_api_key = google_api_key
        self.setup_models()
        # >>> CHANGED: Khởi tạo các thuộc tính để lưu trữ trạng thái qua nhiều file
        self.clear_memory()
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
        return (
            [], # Xóa lịch sử chat
            "", # Xóa text box câu hỏi
            "Sẵn sàng xử lý file mới...", # Reset status
            "Chưa có tài liệu nào được xử lý." # Reset danh sách file
        )
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

    # >>> CHANGED: Cập nhật hàm xử lý PDF để hỗ trợ nhiều file
    def process_pdf(self, pdf_path: str) -> Tuple[str, str]:
        """Xử lý file PDF và thêm vào 'bộ nhớ' của chatbot."""
        try:
            if not pdf_path:
                return "Vui lòng chọn một file PDF.", self._get_processed_files_markdown()

            file_name = Path(pdf_path).name
            if file_name in self.processed_files:
                logger.warning(f"Tệp '{file_name}' đã được xử lý trước đó. Bỏ qua.")
                return f"Tệp '{file_name}' đã được xử lý. Sẵn sàng nhận câu hỏi.", self._get_processed_files_markdown()

            # 1. Trích xuất và làm sạch text
            raw_text = self.extract_text_from_pdf(pdf_path)
            clean_text = self.clean_text(raw_text)

            # 2. Chunking
            structured_chunks = self.powerful_chunking_strategy(clean_text)
            if not structured_chunks:
                return f"Không thể chia nhỏ tài liệu '{file_name}'. File có thể không có nội dung text.", self._get_processed_files_markdown()

            # 3. Chuẩn bị dữ liệu và metadata mới
            new_documents = []
            new_metadata = []
            chunk_id_offset = len(self.documents) # Bắt đầu ID từ số lượng chunk hiện có

            for i, chunk_data in enumerate(structured_chunks):
                combined_text = f"Tiêu đề: {chunk_data['heading']}\nNội dung: {chunk_data['content']}"
                new_documents.append(combined_text)
                new_metadata.append({
                    'chunk_id': chunk_id_offset + i,
                    'source_file': file_name, # Thêm nguồn file
                    'heading': chunk_data['heading'],
                    'length': len(chunk_data['content']),
                    'preview': chunk_data['content'][:150] + "..."
                })
            
            # 4. Tạo embeddings cho các chunk mới
            new_embeddings = self.create_embeddings(new_documents)

            # 5. Nối dữ liệu mới vào "bộ nhớ"
            self.documents.extend(new_documents)
            self.document_metadata.extend(new_metadata)
            if self.embeddings is None:
                self.embeddings = new_embeddings
            else:
                self.embeddings = np.vstack([self.embeddings, new_embeddings])

            self.processed_files.add(file_name) # Thêm file vào danh sách đã xử lý

            total_chunks = len(self.documents)
            status_message = (
                f"Xử lý thành công '{file_name}'!\n"
                f"- Số chunks mới: {len(new_documents)}\n"
                f"- Tổng số chunks trong bộ nhớ: {total_chunks:,}"
            )
            return status_message, self._get_processed_files_markdown()

        except Exception as e:
            error_msg = f"Lỗi xử lý PDF: {str(e)}"
            logger.error(error_msg)
            return error_msg, self._get_processed_files_markdown()

    def _get_processed_files_markdown(self) -> str:
        """Tạo chuỗi markdown hiển thị danh sách các file đã xử lý."""
        if not self.processed_files:
            return "Chưa có tài liệu nào được xử lý."
        
        md_string = "**Các tài liệu trong bộ nhớ:**\n"
        for i, file_name in enumerate(self.processed_files, 1):
            md_string += f"{i}. {file_name}\n"
        return md_string
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

    # >>> CHANGED: Cập nhật hàm generate_answer để sử dụng metadata (source_file)
    def generate_answer(self, query: str, chat_history: List) -> Tuple[str, List]:
        """Tạo câu trả lời dựa trên tài liệu và lịch sử chat"""
        try:
            if not self.documents:
                error_msg = "Vui lòng tải lên và xử lý ít nhất một file PDF trước khi đặt câu hỏi!"
                chat_history.append((query, error_msg))
                return "", chat_history

            relevant_docs = self.search_relevant_documents(query, top_k=5)

            if not relevant_docs or relevant_docs[0][1] < 0.3:
                error_msg = "Tôi không tìm thấy thông tin đủ liên quan trong các tài liệu đã cung cấp để trả lời câu hỏi này."
                chat_history.append((query, error_msg))
                return "", chat_history

            context = ""
            for i, (doc, score, metadata) in enumerate(relevant_docs, 1):
                # Thêm tên file nguồn vào context
                context += f"\n--- Trích dẫn {i} (Từ file: '{metadata['source_file']}', Độ liên quan: {score:.2f}) ---\n{doc}\n"

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

            confidence_score = relevant_docs[0][1]
            confidence_info = f"<br/><br/>---<br/><span style='color: #FF6B6B;'>*Độ tin cậy của nguồn chính: {confidence_score:.2%}*</span>"
            if confidence_score < 0.4:
                confidence_info += " (Thấp - Câu trả lời có thể không liên quan chặt chẽ)"
            elif confidence_score < 0.65:
                confidence_info += " (Trung bình)"
            else:
                confidence_info += " (Cao)"

            final_answer = answer + confidence_info
            chat_history.append((query, final_answer))
            return "", chat_history

        except Exception as e:
            error_msg = f"Lỗi tạo câu trả lời: {str(e)}"
            logger.error(error_msg)
            chat_history.append((query, error_msg))
            return "", chat_history
    # <<< END CHANGED

def create_interface(chatbot: PDFChatbot):
    """Tạo giao diện Gradio"""
    custom_css = """
    .gradio-container { font-family: 'Arial', sans-serif !important; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; }
    .gr-interface { border-radius: 15px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important; }
    .gr-panel { background: rgba(255,255,255,0.95) !important; border-radius: 10px !important; backdrop-filter: blur(10px) !important; }
    .gr-button { background: linear-gradient(45deg, #FF6B6B, #4ECDC4) !important; border: none !important; border-radius: 8px !important; color: white !important; font-weight: bold !important; transition: all 0.3s ease !important; }
    .gr-button:hover { transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important; }
    .gr-textbox { border-radius: 8px !important; border: 2px solid #e0e0e0 !important; transition: border-color 0.3s ease !important; }
    .gr-textbox:focus { border-color: #4ECDC4 !important; box-shadow: 0 0 0 3px rgba(78, 205, 196, 0.1) !important; }
    """

    with gr.Blocks(css=custom_css, title="PDF Chatbot AI", theme=gr.themes.Soft()) as interface:
        gr.HTML("""<div style="text-align: center; margin-bottom: 30px;"><h1 style="color: #2C3E50; font-size: 2.5em; margin-bottom: 10px;">PDF Chatbot AI </h1><p style="color: #7F8C8D; font-size: 1.2em;">Trò chuyện thông minh với nhiều tài liệu PDF cùng lúc</p></div>""")

        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML("<h3 style='color: #34495E;'>1. Tải lên & Xử lý</h3>")

                pdf_input = gr.File(label="Chọn file PDF", file_types=[".pdf"], type="filepath")
                process_btn = gr.Button("Xử lý & Thêm vào bộ nhớ", variant="primary", size="lg")
                
                status_output = gr.Textbox(label="Trạng thái xử lý", lines=5, interactive=False, placeholder="Chờ tải lên file PDF...")
                
                # >>> CHANGED: Thêm khu vực hiển thị các file đã xử lý
                processed_files_display = gr.Markdown(
                    label="Các tài liệu đã được xử lý",
                    value="Chưa có tài liệu nào được xử lý."
                )
                
                clear_memory_btn = gr.Button("Xóa bộ nhớ & Bắt đầu lại", variant="stop")
                # <<< END CHANGED

            with gr.Column(scale=2):
                gr.HTML("<h3 style='color: #34495E;'>2. Trò chuyện với tài liệu</h3>")
                chatbot_interface = gr.Chatbot(label="Cuộc trò chuyện", height=500, show_label=True, elem_id="chatbot")
                with gr.Row():
                    query_input = gr.Textbox(label="", placeholder="Nhập câu hỏi của bạn về các tài liệu...", lines=2, scale=4)
                    send_btn = gr.Button("Gửi", variant="primary", scale=1)

        # Xử lý sự kiện
        # >>> CHANGED: Cập nhật các sự kiện click
        process_btn.click(
            fn=chatbot.process_pdf,
            inputs=[pdf_input],
            outputs=[status_output, processed_files_display]
        )

        send_btn.click(
            fn=chatbot.generate_answer,
            inputs=[query_input, chatbot_interface],
            outputs=[query_input, chatbot_interface]
        )

        query_input.submit(
            fn=chatbot.generate_answer,
            inputs=[query_input, chatbot_interface],
            outputs=[query_input, chatbot_interface]
        )
        
        clear_memory_btn.click(
            fn=chatbot.clear_memory,
            inputs=[],
            # Xóa lịch sử chat, câu hỏi, trạng thái, và danh sách file
            outputs=[chatbot_interface, query_input, status_output, processed_files_display]
        )
        # <<< END CHANGED

        gr.HTML("""
        <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px;">
            <h4 style="color: #2C3E50;">Hướng dẫn sử dụng:</h4>
            <ol style="color: #34495E;">
                <li>Tải lên file PDF của bạn ở cột bên trái.</li>
                <li>Nhấn nút "Xử lý & Thêm vào bộ nhớ" và đợi thông báo thành công.</li>
                <li>Bạn có thể lặp lại bước 1 và 2 để thêm nhiều tài liệu khác.</li>
                <li>Đặt câu hỏi về nội dung của TẤT CẢ các tài liệu ở khung chat bên phải.</li>
                <li>Nếu muốn bắt đầu lại, nhấn "Xóa bộ nhớ & Bắt đầu lại".</li>
            </ol>
        </div>
        """)
    return interface

def main():
    """Hàm chính để chạy ứng dụng"""
    print("Khởi động PDF Chatbot AI...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get Google API key from environment variable
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    if not GOOGLE_API_KEY:
        print("LỖI: Không tìm thấy GOOGLE_API_KEY trong biến môi trường.")
        print("Vui lòng:")
        print("1. Tạo file .env trong thư mục gốc của dự án")
        print("2. Thêm dòng: GOOGLE_API_KEY=your_api_key_here")
        print("3. Thay 'your_api_key_here' bằng API key thực của bạn từ https://makersuite.google.com/app/apikey")
        return

    try:
        chatbot = PDFChatbot(GOOGLE_API_KEY)
        interface = create_interface(chatbot)
        print("Ứng dụng đã sẵn sàng!")
        print("Mở trình duyệt và truy cập địa chỉ được hiển thị (thường là http://127.0.0.1:7860)")
        interface.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
    except Exception as e:  
        print(f"Lỗi nghiêm trọng khi khởi động ứng dụng: {str(e)}")

if __name__ == "__main__":
    main()