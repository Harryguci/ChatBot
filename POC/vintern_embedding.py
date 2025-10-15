!pip install flash_attn
!pip install decord
!pip install transformers==4.48.0
import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer, AutoProcessor
import matplotlib.pyplot as plt

model_name = "5CD-AI/Vintern-Embedding-1B"

processor =  AutoProcessor.from_pretrained(
    model_name,
    trust_remote_code=True
)
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
).eval().cuda()
!wget https://huggingface.co/5CD-AI/ColVintern-1B-v1/resolve/main/ex1.jpg
!wget https://huggingface.co/5CD-AI/ColVintern-1B-v1/resolve/main/ex2.jpg
images = [Image.open("ex1.jpg"), Image.open("ex2.jpg")]
batch_images = processor.process_images(images)

queries = [
    "Cảng Hải Phòng ở đâu ?",
    "Phí giao hàng bao nhiêu ?",
]
batch_queries = processor.process_queries(queries)

text_documents = [
    "Cảng Hải Phòng là một cụm cảng biển tổng hợp cấp quốc gia, lớn thứ 2 ở Việt Nam sau cảng Sài Gòn, là cửa ngõ quốc tế của Việt Nam, nằm tại ba quận Hồng Bàng, Ngô Quyền và Hải An. Bên cạnh đó, cùng tên Cảng Hải Phòng (tiếng Anh: Port of Hai Phong hoặc Hai Phong Port) là một cụm cảng biển thuộc Công ty cổ phần cảng Hải Phòng tại thành phố Hải Phòng, Việt Nam. Đây là một trong hai cảng biển tổng hợp lớn và lâu đời nhất tại Việt Nam, cùng với Công ty Cảng Sài Gòn ở phía Nam.",
    "Sân bay Chu Lai (tỉnh Quảng Nam) cũng được hãng hàng không giá rẻ Vietjet đề xuất đầu tư nâng cấp 20.000 tỉ đồng theo 3 giai đoạn từ 2020-2025 để đến năm 2025 trở thành Cảng hàng không quốc tế và trở thành trung tâm trung chuyển, vận tải hàng hóa lớn của cả nước theo quy hoạch của Bộ GTVT năm 2015.",
]
batch_text_docs = processor.process_docs(text_documents)

raw_docs = images + text_documents

# ==============================
# 3. Move Tensors to GPU
# ==============================
batch_images["pixel_values"] = batch_images["pixel_values"].cuda().bfloat16()
batch_images["input_ids"] = batch_images["input_ids"].cuda()
batch_images["attention_mask"] = batch_images["attention_mask"].cuda().bfloat16()

batch_queries["input_ids"] = batch_queries["input_ids"].cuda()
batch_queries["attention_mask"] = batch_queries["attention_mask"].cuda().bfloat16()

batch_text_docs["input_ids"] = batch_text_docs["input_ids"].cuda()
batch_text_docs["attention_mask"] = batch_text_docs["attention_mask"].cuda().bfloat16()

# ==============================
# 4. Generate Embeddings
# ==============================
with torch.no_grad():
    image_embeddings = model(**batch_images)
    query_embeddings = model(**batch_queries)
    text_docs_embeddings = model(**batch_text_docs)

# ==============================
# 5. Compute Similarity Scores
# ==============================
scores = processor.score_multi_vector(
    query_embeddings,
    list(image_embeddings) + list(text_docs_embeddings)
)

max_scores, max_indices = torch.max(scores, dim=1)

# ==============================
# 6. Print Results
# ==============================
for i, query in enumerate(queries):
    print("=" * 100)
    print(f"Query: '{query}'")
    print(f"Score: {max_scores[i].item()}\n")

    doc = raw_docs[max_indices[i]]
    if isinstance(doc, str):
        print(f"Matched Text Document:\n{doc}\n")
    else:
        plt.figure(figsize=(5, 5))
        plt.imshow(doc)
        plt.axis("off")
        plt.show()
pip install --upgrade pymupdf
!wget https://datafiles.chinhphu.vn/cpp/files/vbpq/2019/12/100.signed_01.pdf
!wget https://datafiles.chinhphu.vn/cpp/files/vbpq/2019/12/100_2.pdf
!gdown 1w6jTTm6jTm0JzmQPwe_1POJ_AEZx__ri
!wget https://huggingface.co/datasets/khang119966/video/resolve/main/trieu_chung_benh.txt
import tqdm
import fitz
from datasets import load_dataset
page_list = []
for pdffile in ["100.signed_01.pdf","Địa lí 9.pdf"]:
  doc = fitz.open(pdffile)
  for index in tqdm.tqdm(range(doc.page_count)):
      page = doc.load_page(index)
      pix = page.get_pixmap()
      img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
      page_list.append(img)
page_list = page_list[:200]
image_embeddings_list = []

for i in tqdm.tqdm(range(len(page_list))):
    batch_images = processor.process_images([page_list[i]])

    batch_images["pixel_values"] =  batch_images["pixel_values"].cuda().bfloat16()
    batch_images["input_ids"] = batch_images["input_ids"].cuda() #.bfloat16()
    batch_images["attention_mask"] = batch_images["attention_mask"].cuda().bfloat16()

    with torch.no_grad():
        image_embeddings = model(**batch_images)

    image_embeddings_list.append(image_embeddings.squeeze())
len(image_embeddings_list)
def split_text(text, chunk_size=1024, overlap=512):
    chunks = []
    start = 0
    if not isinstance(text, str):
        return []
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

with open("trieu_chung_benh.txt", 'r', encoding='utf-8') as f:
    content = f.read()
    text_chunk_list = split_text(content)

text_chunk_list = text_chunk_list[:200]
text_embeddings_list = []

for chunk in tqdm.tqdm(text_chunk_list):
  batch_text_docs = processor.process_docs([chunk])

  batch_text_docs["input_ids"] = batch_text_docs["input_ids"].cuda()
  batch_text_docs["attention_mask"] = batch_text_docs["attention_mask"].cuda().bfloat16()

  with torch.no_grad():
      text_docs_embeddings = model(**batch_text_docs)
      text_embeddings_list += list(text_docs_embeddings)
doc_embeddings_list = text_embeddings_list + image_embeddings_list
raw_docs = text_chunk_list + page_list
def search_and_print(query, processor, model, doc_embeddings_list, raw_docs, top_k=5, device="cuda"):
    """
    Tìm kiếm và in ra kết quả top_k tài liệu liên quan đến query.
    - query: câu truy vấn (string)
    - processor: processor đã load
    - model: model encode query
    - doc_embeddings_list: list embedding tài liệu
    - raw_docs: list tài liệu gốc (text hoặc hình ảnh)
    - top_k: số kết quả muốn hiển thị
    """
    # Chuẩn bị batch query
    batch_queries = processor.process_queries([query])
    batch_queries["input_ids"] = batch_queries["input_ids"].to(device)
    batch_queries["attention_mask"] = batch_queries["attention_mask"].to(device).bfloat16()

    # Tính embedding query
    with torch.no_grad():
        query_embeddings = model(**batch_queries)

    # Tính điểm tương đồng
    scores = processor.score_multi_vector(query_embeddings, doc_embeddings_list)[0]
    top_indices = scores.argsort(descending=True)[:top_k]

    print(f"\n🔍 Kết quả tìm kiếm cho query: \"{query}\"\n")
    for rank, idx in enumerate(top_indices, start=1):
        score = scores[idx].item()
        doc = raw_docs[idx]

        print(f"#{rank} | Score: {score:.4f}")
        print("=" * 60)
        if isinstance(doc, str):
            print(f"📄 Văn bản: {doc}\n")
        else:
            print("🖼️ Hình ảnh:")
            plt.figure(figsize=(10, 10))
            plt.imshow(doc)
            plt.axis("off")
            plt.show()
search_and_print("Đi xe ngược chiều bị phạt bao nhiêu tiền ?", processor, model, doc_embeddings_list, raw_docs, top_k=5)