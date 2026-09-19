# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Đinh Trường An
**Nhóm:** G24
**Ngày:** 19/9/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine cao nghĩa là hai vector embedding hướng gần nhau, nên hai câu có nội dung/ngữ nghĩa gần nhau. Điểm gần 1 biểu thị mức tương đồng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên cần trả sách thư viện trước ngày đến hạn.
- Câu B: Người học phải hoàn trả tài liệu đúng hạn.
- Tại sao tương đồng: Khác từ vựng nhưng cùng nói về nghĩa vụ trả tài liệu đúng hạn.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Giảng viên được mượn tối đa năm tài liệu.
- Câu B: Thư viện mở cửa từ thứ Hai đến thứ Sáu.
- Tại sao khác: Một câu nói về hạn mức mượn, câu kia nói về giờ phục vụ.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine đo góc giữa các vector nên ít bị ảnh hưởng bởi độ dài văn bản/vector. Đây là đặc tính phù hợp với embedding đã chuẩn hóa, nơi hướng vector biểu diễn ý nghĩa tốt hơn độ lớn tuyệt đối.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: ceil((10.000 − 50) / (500 − 50)) = ceil(9.950 / 450) = 23.
> Đáp án: 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Với overlap 100: ceil((10.000 − 100) / (500 − 100)) = ceil(9.900 / 400) = 25 chunks. Overlap lớn giữ được ngữ cảnh ở ranh giới chunk, đổi lại tốn thêm lưu trữ và embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"(?<=[.!?])\s+", text.strip())` để tách sau dấu kết câu nhưng vẫn giữ dấu câu. Text rỗng trả `[]`; các câu được strip rồi gom theo `max_sentences_per_chunk`. Edge case còn hạn chế là chữ viết tắt và số thập phân có thể bị tách nhầm.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thử separator theo thứ tự đoạn, dòng, câu, khoảng trắng và cuối cùng là ký tự; mảnh quá dài tiếp tục đệ quy với separator nhỏ hơn. Sau đó các mảnh nhỏ liền kề được gom đến gần `chunk_size`. Base case là text rỗng, text đã đủ ngắn, hoặc hết separator thì cắt an toàn theo kích thước cố định.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mỗi `Document` là một record in-memory gồm id, content, metadata copy và embedding; store không tự chunk. Query được embed rồi xếp hạng theo dot product với embedding đã chuẩn hóa, tương đương cosine similarity.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc metadata trước khi similarity search để không bị các kết quả sai audience chiếm top-k. `delete_document` loại toàn bộ records có `metadata['doc_id']` trùng doc_id gốc và trả Boolean theo việc có record bị xóa hay không.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent lấy top-k rồi dựng context đánh số `[1]`, `[2]` kèm source và nội dung chunk. Prompt yêu cầu chỉ dùng context, trích số chunk hỗ trợ, và nói rõ không tìm thấy nếu context thiếu; store rỗng không gọi LLM.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
42 passed in 0.19s
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên cần trả sách thư viện trước ngày đến hạn. | Người học phải hoàn trả tài liệu đúng hạn. | cao | 0.6110 | Có |
| 2 | Giảng viên được mượn tối đa năm tài liệu. | Thư viện mở cửa từ thứ Hai đến thứ Sáu. | thấp | 0.2704 | Có |
| 3 | Tôi muốn gia hạn sách đang mượn. | Có thể kéo dài thời hạn mượn tài liệu không? | cao | 0.5307 | Có |
| 4 | Sách tham khảo bị trả muộn sẽ bị phạt. | Trường tổ chức lễ tốt nghiệp vào tháng Sáu. | thấp | 0.1181 | Có |
| 5 | Sinh viên VinUni được mượn ba tài liệu trong hai tuần. | VinUni cho sinh viên mượn tối đa ba cuốn trong 14 ngày. | cao | 0.8447 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 5 cao nhất dù hai câu dùng “ba tài liệu”, “ba cuốn”, “hai tuần” và “14 ngày”, cho thấy embedding liên kết được cách diễn đạt tương đương. Cặp 3 cũng cùng ý nhưng điểm thấp hơn, nhắc rằng embedding đo mức gần nghĩa liên tục chứ không phải nhãn đúng/sai tuyệt đối.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Tôi được mượn tối đa bao nhiêu tài liệu và giữ trong bao lâu? | graduate-borrowing, chunk 2; marker undergraduate ở rank 2 | 0.033 (RRF) | Có, top-2 | Context top-3 có hạn mức graduate và undergraduate; 1/2 |
| 2 | Phạt quá hạn tài liệu thường là bao nhiêu? | library-faq, chunk 5 | 0.031 (RRF) | Có, top-2 | Chunk FAQ chứa mức 20,000 VND/ngày; 1/2 |
| 3 | Tôi có thể gia hạn tài liệu đang quá hạn không? Điều kiện gia hạn là gì? | circulation-privileges, chunk 2 | 0.032 (RRF) | Có, top-1 | Điều kiện không có người đặt trước; 2/2 |
| 4 | Làm sao để trả sách khi thư viện đóng cửa? | library-faq, chunk 11 | 0.032 (RRF) | Có, top-3 | Có 24/7-return-station; 1/2 |
| 5 | Sách Course Reserve được mượn bao lâu và phải trả ở đâu? | course-reserve, chunk 1 | 0.033 (RRF) | Có, top-1 | Context chứa Circulation Desk và tối đa 2 giờ; 2/2 |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

> Benchmark dùng sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384 chiều). Bản cuối dùng HeadingChunker tách FAQ theo cặp hỏi–đáp, bilingual query expansion Việt–Anh và Reciprocal Rank Fusion (RRF), đạt **7/10**. RRF score (~0.03) là điểm hợp nhất thứ hạng, không phải cosine. Failure còn lại là câu 1–2 chỉ có marker ở rank 2 do quyền mượn/biểu phí bị cạnh tranh bởi các chunk cùng chủ đề.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Metadata chỉ hữu ích khi cách tách dữ liệu khớp với chiều filter: chính sách sinh viên và giảng viên nên thành các tài liệu/chunk riêng. Tôi cũng học được rằng phải kiểm nội dung chunk chứa marker đáp án, không được chỉ nhìn doc_id ở top-k.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 7 / 10 |
| **Tổng phần cá nhân** | **57 / 60** |
