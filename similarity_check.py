"""Print real embedding cosine scores for REPORT_CANHAN section 4."""

from src.chunking import compute_similarity
from src.embeddings import LocalEmbedder

PAIRS = [
    ("Sinh viên cần trả sách thư viện trước ngày đến hạn.", "Người học phải hoàn trả tài liệu đúng hạn."),
    ("Giảng viên được mượn tối đa năm tài liệu.", "Thư viện mở cửa từ thứ Hai đến thứ Sáu."),
    ("Tôi muốn gia hạn sách đang mượn.", "Có thể kéo dài thời hạn mượn tài liệu không?"),
    ("Sách tham khảo bị trả muộn sẽ bị phạt.", "Trường tổ chức lễ tốt nghiệp vào tháng Sáu."),
    ("Sinh viên VinUni được mượn ba tài liệu trong hai tuần.", "VinUni cho sinh viên mượn tối đa ba cuốn trong 14 ngày."),
]


def main() -> None:
    embedder = LocalEmbedder()
    print(f"Embedding backend: {embedder._backend_name}")
    for index, (sentence_a, sentence_b) in enumerate(PAIRS, start=1):
        score = compute_similarity(embedder(sentence_a), embedder(sentence_b))
        prediction = "cao" if index in {1, 3, 5} else "thấp"
        print(f"{index}. prediction={prediction}; score={score:.4f}")
        print(f"   A: {sentence_a}")
        print(f"   B: {sentence_b}")


if __name__ == "__main__":
    main()
