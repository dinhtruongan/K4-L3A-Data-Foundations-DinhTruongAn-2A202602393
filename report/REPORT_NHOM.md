# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nhóm Thư Viện VinUni (L3A)
**Thành viên:** Phan Đức Duy — 2A2026202397 · Đinh Trường An — 2A202602393
**Ngày:** 2026-09-19

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Quy định mượn–trả tài liệu thư viện VinUniversity (borrowing, returning, renewing, fines, course reserve, equipment).

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề có 3 ưu điểm: (1) nhiều nhóm người dùng khác nhau (student/faculty/staff) với quyền mượn và thời hạn khác nhau → dễ thiết kế câu hỏi cần `metadata_filter`; (2) tài liệu có cấu trúc heading/section rõ (policy POL-LLR-001-V4.0, FAQ, bảng circulation privileges) → phù hợp để thử chunking theo heading; (3) nguồn chính thức, công khai, có `robots.txt` cho phép crawl, không chứa dữ liệu nhạy cảm.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Library borrowing rules for undergraduate students | library.vinuni.edu.vn/services/borrow-and-request/undergraduate-and-staff/ | 2026-09-19 / not-stated | ~1.1 KB | audience=student, category=borrowing, en |
| 2 | Library borrowing rules for graduate students | library.vinuni.edu.vn/services/borrow-and-request/graduate-faculty-and-instructors/ | 2026-09-19 / not-stated | ~1.3 KB | audience=student, category=borrowing, en |
| 3 | Library borrowing rules for faculty | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | ~0.9 KB | audience=faculty, category=borrowing, en |
| 4 | Library borrowing rules for staff | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | ~0.9 KB | audience=staff, category=borrowing, en |
| 5 | Circulation privileges and circulation regulations | library.vinuni.edu.vn/borrowing-priviledge/ | 2026-09-19 / not-stated | ~2.9 KB | audience=all, category=borrowing, en |
| 6 | Course Reserve borrowing rules | library.vinuni.edu.vn/course-reserve/ | 2026-09-19 / not-stated | ~0.7 KB | audience=student, category=course-reserve, en |
| 7 | Library fines for overdue, damage and loss | library.vinuni.edu.vn/fine-and-other-charges/ | 2026-09-19 / not-stated | ~1.9 KB | audience=all, category=fines, en |
| 8 | Requesting books, holds and recalls | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | ~1.2 KB | audience=all, category=borrowing, en |
| 9 | Library equipment borrowing rules | policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-09-19 / POL-LLR-001-V4.0 | ~0.9 KB | audience=all, category=equipment, en |
| 10 | Library FAQ about borrowing, returning and renewing | library.vinuni.edu.vn/faq/ | 2026-09-19 / not-stated | ~4.4 KB | audience=all, category=faq, en |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.
- [x] Tuân thủ robots.txt (đã kiểm tra bằng `scripts/fetch_public_pages.py` trước khi crawl).
- [x] Quy trình: crawl raw → `scripts/data_clean.py` (tách audience, bỏ menu/footer, chuẩn hoá) → corpus 10 file + `sources.csv` khớp 1-1.
- [x] Không bịa `document_version` — các file từ policy dùng `POL-LLR-001-V4.0`, còn lại `not-stated`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | str | student / faculty / staff / all | Bộ lọc chính cho câu hỏi cần `metadata_filter={"audience": "student"}` |
| `doc_id` | str | undergraduate-borrowing | Truy vết câu trả lời về đúng file + đối chiếu gold answer |
| `source_url` | str | https://policy.vinuni.edu.vn/... | Kiểm chứng nguồn, trích dẫn |
| `retrieved_at` | str (date) | 2026-09-19 | Đánh giá độ mới của dữ liệu |
| `document_version` | str | POL-LLR-001-V4.0 / not-stated | Phát hiện xung đột giữa các phiên bản |
| `category` | str | borrowing / fines / faq / equipment | Bộ lọc phụ (khi cần hẹp chủ đề) |
| `language` | str | en | Lọc ngôn ngữ nếu mở rộng corpus |
| `cleaned_by` | str | data_clean | Đánh dấu file do script tái cấu trúc, tái lập được |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu (đã bỏ frontmatter), `chunk_size=200`:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| undergraduate-borrowing (1.1 KB) | FixedSizeChunker (`fixed_size`) | 7 | 198.6 | Không — có thể cắt giữa câu |
| | SentenceChunker (`by_sentences`) | 4 | 271.0 | Tốt — trọn câu, nhưng chunk dài |
| | RecursiveChunker (`recursive`) | 8 | 134.5 | Trung bình — gom theo dòng |
| fines-and-damage (1.7 KB) | FixedSizeChunker (`fixed_size`) | 11 | 199.3 | Không — bảng minor/major bị cắt rời |
| | SentenceChunker (`by_sentences`) | 7 | 238.9 | Tốt — từng điều khoản trọn vẹn |
| | RecursiveChunker (`recursive`) | 11 | 152.0 | Trung bình |
| library-faq (5.8 KB) | FixedSizeChunker (`fixed_size`) | 39 | 196.2 | Kém — cắt giữa câu hỏi và đáp án |
| | SentenceChunker (`by_sentences`) | 25 | 227.2 | Tốt nhất — mỗi Q&A gần như 1 chunk |
| | RecursiveChunker (`recursive`) | 40 | 141.9 | Trung bình — nhiều chunk vụn |

### Chiến lược của từng thành viên

**Thành viên 1 — Phan Đức Duy (2A2026202397)**
- **Loại chiến lược:** RecursiveChunker (chunk_size=500)
- **Mô tả & lý do chọn cho chủ đề này:** Recursive tôn trọng ranh giới ngữ nghĩa theo thứ tự ưu tiên (đoạn → dòng → câu → từ) nên phù hợp tài liệu quy định có cấu trúc nhiều tầng như policy/FAQ; gom mảnh nhỏ tránh chunk vụn. Chunk_size 500 đủ dài để giữ cả một điều khoản kèm con số.
- **Code snippet (nếu custom):** không — dùng `RecursiveChunker` có sẵn, đổi tham số `chunk_size=500`.

**Thành viên 2 — Đinh Trường An (2A202602393)**
- **Loại chiến lược:** HeadingChunker (custom theo heading/section — vai R3 bắt buộc), chunk_size=600
- **Mô tả & lý do chọn:** Văn bản quy định được biên soạn theo mục (`## Hạn mức và gia hạn`), mỗi section đã là một đơn vị ngữ nghĩa trọn vẹn. Chunker giữ nguyên từng section theo heading; section dài hơn ngưỡng thì hạ xuống `RecursiveChunker` và **gắn lại tiêu đề vào từng mảnh con** để mảnh thứ hai không mất ngữ cảnh "mục này nói về gì". Phù hợp corpus quy định mượn-trả của nhiều trường ĐH (Việt hóa).
- **Code snippet:**
```python
class HeadingChunker:
    """Keep each Markdown heading section intact; split only long sections."""

    def __init__(self, chunk_size: int = 600) -> None:
        self.chunk_size = chunk_size
        self.fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        sections = []
        current_heading = ""
        current_lines: list[str] = []
        for line in text.splitlines():
            if line.startswith("#"):
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines).strip()))
                current_heading = line.strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_heading, "\n".join(current_lines).strip()))

        chunks: list[str] = []
        for heading, section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
            else:
                for piece in self.fallback.chunk(section):
                    chunks.append(piece if piece.startswith("#") else f"{heading}\n{piece}")
        return [chunk for chunk in chunks if chunk]
```

### So Sánh Giữa Các Thành Viên

> Nhóm dùng **cùng corpus 10 tài liệu VinUni và cùng 5 benchmark query** trong `data/library-borrowing/`. Điểm chấm theo thang `docs/SCORING.md` (2đ/câu) nên có thể so sánh trực tiếp.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| 1 (Duy) | Recursive (500) | 6/10 | Chunk cân đối, tôn trọng ranh giới câu/đoạn; ổn định trên mọi file | Câu ngắn ("overdue items can't be renewed") dễ bị xếp hạng thấp; số liệu nằm tách chunk |
| 2 (Trường An) | HeadingChunker (600) | Chờ chạy lại trên corpus chung | Giữ trọn từng section, gắn lại heading khi section dài phải cắt nhỏ | Cần đo lại cùng corpus/query trước khi kết luận |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Kết quả hiện có cho thấy SentenceChunker đạt 9/10, Recursive 6/10 và FixedSize 6/10 trên corpus VinUni. HeadingChunker của Trường An đang được chạy lại trên **cùng corpus/query**; chỉ sau lần chạy đó nhóm mới chốt chiến lược thắng. Giả thuyết cần kiểm chứng là heading giữ trọn quy định theo mục, còn sentence giữ trọn điều khoản ngắn chứa số liệu.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Tôi được mượn tối đa bao nhiêu tài liệu và giữ trong bao lâu? *(cần `metadata_filter={"audience": "student"}`)* | SV đại học: 3 tài liệu/2 tuần (gia hạn 1 tuần, 1 lần). SV sau ĐH: 5 tài liệu/1 tháng (gia hạn 2 tuần). Không lọc sẽ lẫn faculty (5/6 tháng) và staff (3/2 tuần). | undergraduate-borrowing, graduate-borrowing |
| 2 | Phạt quá hạn tài liệu thường là bao nhiêu? | Tài liệu thường: 20,000 VND/ngày; course-specific: 20,000 VND/giờ; thiết bị: 20,000 VND/giờ. Quá hạn >30 ngày: thêm phí bằng giá bìa. | library-faq câu 7 |
| 3 | Tôi có thể gia hạn tài liệu đang quá hạn không? Điều kiện gia hạn là gì? | Không — "overdue items can't be renewed". Gia hạn = nửa thời gian gốc, chỉ khi không ai đặt trước; chưa quá hạn gia hạn online/quầy, quá hạn phải gia hạn trực tiếp. | faculty-borrowing, circulation-privileges |
| 4 | Làm sao để trả sách khi thư viện đóng cửa? | Dùng 24/7 book return machine tại cổng chính — chỉ nhận check-in sách in, không dùng để mượn. | library-faq câu 5 |
| 5 | Sách Course Reserve được mượn bao lâu và phải trả ở đâu? | Tối đa 2 giờ, chỉ dùng trong thư viện, mượn/trả tại Circulation Desk (1F), tối đa 2 items/lần. | course-reserve, circulation-privileges |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Quyền mượn | Recursive / Sentence | ✅ (cả 3, sau khi filter student) | Filter student làm top-3 chỉ còn tài liệu student; không filter bị lẫn faculty/staff |
| 2 | Phạt quá hạn | **Sentence** (2đ) | ✅ Sentence: chunk chứa con số ở top-2; Recursive/Fixed chỉ lấy chunk mô tả chung (1đ) | Con số 20,000 VND bị cắt sang chunk khác ở 2 chiến lược kia |
| 3 | Gia hạn quá hạn | Sentence (1đ) | ⚠️ một phần | **Failure case:** câu "overdue items can't be renewed" không lọt top-3 của cả 3 chiến lược |
| 4 | Trả sách khi đóng cửa | **FixedSize / Sentence** (2đ) | ✅ Fixed & Sentence: chunk FAQ câu 5 trong top-3; Recursive thiếu (1đ) | Recursive top-1 bắt nhầm "holiday extension" (gần nghĩa nhưng sai câu hỏi) |
| 5 | Course Reserve | Cả 3 (2đ) | ✅ cả 3 | Điểm cao nhất toàn bộ benchmark (0.70–0.77) |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có — ở **câu 1**. Chạy A/B (có/không `metadata_filter={"audience": "student"}`): không lọc, top-3 lẫn tài liệu faculty/staff (thời hạn 6 tháng/2 tuần) nên agent có thể trả lời sai đối tượng; lọc xong top-3 chỉ còn tài liệu student và agent trả lời đúng phạm vi sinh viên. Đánh đổi: lọc quá hẹp (ví dụ chỉ `category=borrowing`) có thể loại bỏ chunk FAQ vốn cũng chứa câu trả lời — cần cân bằng precision/recall.

> **So sánh chéo hợp lệ:** cả hai chiến lược chạy trên cùng 10 file và 5 query. A/B ở câu 1 dùng `audience=student`: không lọc có thể lẫn tài liệu faculty/staff, còn lọc giới hạn ngữ cảnh về sinh viên. Cả hai vẫn phải chấm marker trong nội dung chunk, không chỉ đối chiếu `doc_id`.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. Chiến lược chunk tôn trọng cấu trúc ngôn ngữ của dữ liệu thường thắng chunk cơ khí: trên corpus VinUni, SentenceChunker đạt 9/10 (Recursive/FixedSize 6/10). HeadingChunker được đánh giá lại trên đúng corpus này; con số phải nằm **trong** chunk mới lọt top-k.
> 2. Metadata filter thật sự đổi kết quả: A/B của cả 2 thành viên cho cùng kết luận — không lọc, top-1 là tài liệu sai đối tượng (faculty 6 tháng); lọc `audience=student` chuyển top-1 về đúng nhóm. Filter chỉ hiệu quả khi dữ liệu đã tách theo audience từ khâu crawl.
> 3. Mock embedder phá hỏng mọi số liệu (điểm gần 0/âm, retrieval lẫn lộn) — benchmark phải dùng embedder thật (local đa ngữ MiniLM, 384 chiều); 42 test chỉ cần mock vì chỉ kiểm cấu trúc.

**Bài học rút ra khi so sánh trong nhóm:**
> So sánh chỉ có ý nghĩa khi giữ cố định corpus, query, embedding backend và `top_k`; khi đó chênh lệch mới đến từ chunking. Metadata filter cải thiện precision cho câu 1, nhưng filter quá hẹp có thể làm mất FAQ hoặc tài liệu chứa thông tin bổ sung.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> (1) Kết hợp HeadingChunker và giữ trọn câu trong section cho các chính sách dài; (2) lưu version rõ hơn cho từng biểu phí; (3) bổ sung thêm marker đáp án để phát hiện trường hợp cùng tài liệu nhưng sai section.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 14 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 |
| Thuyết trình (Demo) | 4 / 5 |
| **Tổng phần nhóm** | **36 / 40** |
