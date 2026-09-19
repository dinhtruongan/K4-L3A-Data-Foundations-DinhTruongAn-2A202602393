"""Run the individual retrieval benchmark for the library-services corpus."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from src.chunking import RecursiveChunker
from src.embeddings import EMBEDDING_PROVIDER_ENV, LocalEmbedder, _mock_embed
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/library-borrowing")


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


# Personal strategy: switch this line for a controlled comparison.
CHUNKER = HeadingChunker(chunk_size=600)

BENCHMARKS = [
    {
        "query": "Tôi được mượn tối đa bao nhiêu tài liệu và giữ trong bao lâu?",
        "gold_answer": "Undergraduate: 3 tài liệu/2 tuần; graduate: 5 tài liệu/1 tháng.",
        "answer_marker": "Undergraduate students may borrow up to 3 items during two weeks",
        "metadata_filter": {"audience": "student"},
    },
    {
        "query": "Phạt quá hạn tài liệu thường là bao nhiêu?",
        "gold_answer": "20,000 VND/ngày; course-specific và thiết bị: 20,000 VND/giờ.",
        "answer_marker": "20,000 VND per day",
        "metadata_filter": None,
    },
    {
        "query": "Tôi có thể gia hạn tài liệu đang quá hạn không? Điều kiện gia hạn là gì?",
        "gold_answer": "Không gia hạn tài liệu quá hạn; chỉ khi không có người đặt trước.",
        "answer_marker": "Overdue items can't be renewed",
        "metadata_filter": None,
    },
    {
        "query": "Làm sao để trả sách khi thư viện đóng cửa?",
        "gold_answer": "Dùng máy trả sách 24/7 ở cổng chính.",
        "answer_marker": "24/7-return-station",
        "metadata_filter": None,
    },
    {
        "query": "Sách Course Reserve được mượn bao lâu và phải trả ở đâu?",
        "gold_answer": "Tối đa 2 giờ; mượn/trả tại Circulation Desk tầng 1.",
        "answer_marker": "checked out for 02 hours only",
        "metadata_filter": None,
    },
]


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    """Read simple YAML front matter and return metadata plus clean body."""
    text = path.read_text(encoding="utf-8")
    _, front_matter, content = text.split("---", 2)
    metadata: dict[str, str] = {}
    for line in front_matter.splitlines():
        key, colon, value = line.partition(":")
        if colon:
            metadata[key.strip()] = value.strip().strip('"')
    return metadata, content.strip()


def load_chunked_documents() -> list[Document]:
    """Chunk each clean corpus document outside of the embedding store."""
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        metadata, content = parse_markdown(path)
        for index, chunk in enumerate(CHUNKER.chunk(content)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={**metadata, "doc_id": path.stem, "chunk_index": index},
                )
            )
    return documents


def get_embedder():
    """Use the configured local semantic model, with a safe mock fallback."""
    load_dotenv(override=False)
    if os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower() == "local":
        try:
            return LocalEmbedder()
        except Exception as error:
            print(f"Local embedding unavailable; using mock fallback: {error}")
    return _mock_embed


def retrieve(store: EmbeddingStore, query: str, metadata_filter: dict | None) -> list[dict]:
    """Use the same semantic retrieval route for every chunking strategy."""
    return store.search_with_filter(query, top_k=3, metadata_filter=metadata_filter)


def main() -> None:
    documents = load_chunked_documents()
    embedder = get_embedder()
    store = EmbeddingStore(collection_name="library_services_benchmark", embedding_fn=embedder)
    store.add_documents(documents)

    print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")
    print(f"Chunker: {CHUNKER.__class__.__name__}")
    print(f"Chunks loaded: {store.get_collection_size()} from {len(list(DATA_DIR.glob('*.md')))} files")

    for number, benchmark in enumerate(BENCHMARKS, start=1):
        metadata_filter = benchmark["metadata_filter"]
        results = retrieve(store, benchmark["query"], metadata_filter)
        print(f"\n[{number}] {benchmark['query']}")
        print(f"Gold: {benchmark['gold_answer']}")
        print(f"Filter: {metadata_filter or 'none'}")
        marker_rank = next(
            (rank for rank, result in enumerate(results, start=1) if benchmark["answer_marker"] in result["content"]),
            None,
        )
        retrieval_points = 2 if marker_rank == 1 else 1 if marker_rank else 0
        print(f"Content score: {retrieval_points}/2 (answer marker rank: {marker_rank or 'absent'})")
        for rank, result in enumerate(results, start=1):
            preview = " ".join(result["content"].split())[:200]
            print(
                f"  {rank}. score={result['score']:.3f} "
                f"doc_id={result['metadata']['doc_id']} chunk={result['metadata']['chunk_index']}"
            )
            print(f"     {preview}")


def run_filter_ab() -> None:
    """Run the required filtered/unfiltered comparison for benchmark query 1."""
    benchmark = BENCHMARKS[0]
    documents = load_chunked_documents()
    store = EmbeddingStore(collection_name="library_services_ab", embedding_fn=get_embedder())
    store.add_documents(documents)

    print("\n=== A/B metadata filter: query 1 ===")
    for label, metadata_filter in (("with audience=student", {"audience": "student"}), ("without filter", None)):
        results = retrieve(store, benchmark["query"], metadata_filter)
        print(f"{label}:")
        for rank, result in enumerate(results, start=1):
            contains_marker = benchmark["answer_marker"] in result["content"]
            print(f"  {rank}. {result['metadata']['doc_id']} score={result['score']:.3f} marker={contains_marker}")


if __name__ == "__main__":
    main()
    run_filter_ab()
