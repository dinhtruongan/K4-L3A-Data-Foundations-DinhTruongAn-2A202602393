"""Run the individual retrieval benchmark for the library-services corpus."""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from src.chunking import RecursiveChunker
from src.embeddings import EMBEDDING_PROVIDER_ENV, LocalEmbedder, _mock_embed
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/library-borrowing")


class HeadingChunker:
    """Chunk by Markdown headings and numbered FAQ question/answer sections."""

    def __init__(self, chunk_size: int = 600, grace: int = 150) -> None:
        self.chunk_size = chunk_size
        self.grace = grace
        self.fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        sections: list[tuple[str, str]] = []
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
            for subsection in self._split_faq_sections(heading, section):
                if len(subsection) <= self.chunk_size + self.grace:
                    chunks.append(subsection)
                    continue
                for piece in self.fallback.chunk(subsection):
                    chunks.append(piece if piece.startswith("#") else f"{heading}\n{piece}")
        return [chunk for chunk in chunks if chunk]

    @staticmethod
    def _split_faq_sections(heading: str, section: str) -> list[str]:
        """Keep each numbered FAQ question together with its following answer."""
        lines = section.splitlines()
        if len(lines) < 2:
            return [section]

        title, body = lines[0], lines[1:]
        groups: list[list[str]] = []
        current: list[str] = []
        for line in body:
            is_labeled_subsection = re.match(r"^[A-Z][A-Za-z ]{1,40}:$", line.strip())
            if is_labeled_subsection and current:
                groups.append(current)
                current = [line]
                continue
            if re.match(r"^\d+\.\s+.+\?\s*$", line.strip()) and current:
                groups.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            groups.append(current)

        # Ordinary policy text has no FAQ questions and remains one heading section.
        if len(groups) <= 1:
            return [section]
        return [f"{title}\n" + "\n".join(group).strip() for group in groups]


# Personal strategy: switch this line for a controlled comparison.
CHUNKER = HeadingChunker(chunk_size=600)

BENCHMARKS = [
    {
        "query": "Tôi được mượn tối đa bao nhiêu tài liệu và giữ trong bao lâu?",
        "english_query": "How many library items may I borrow and for how long?",
        "gold_answer": "Undergraduate: 3 tài liệu/2 tuần; graduate: 5 tài liệu/1 tháng.",
        "answer_marker": "Undergraduate student 3 2 weeks",
        "metadata_filter": {"audience": "student"},
    },
    {
        "query": "Phạt quá hạn tài liệu thường là bao nhiêu?",
        "english_query": "What is the overdue fine for library materials?",
        "gold_answer": "20,000 VND/ngày; course-specific và thiết bị: 20,000 VND/giờ.",
        "answer_marker": "Normal material: 20,000 VND/ day overdue/ document.",
        "metadata_filter": None,
    },
    {
        "query": "Tôi có thể gia hạn tài liệu đang quá hạn không? Điều kiện gia hạn là gì?",
        "english_query": "Can overdue library materials be renewed and what are the renewal conditions?",
        "gold_answer": "Gia hạn bằng nửa thời hạn gốc, chỉ khi không có người đặt trước; tài liệu quá hạn phải xử lý trực tiếp tại quầy.",
        "answer_marker": "Renewals of library materials are only allowed if there has been no request for that material by others.",
        "metadata_filter": None,
    },
    {
        "query": "Làm sao để trả sách khi thư viện đóng cửa?",
        "english_query": "How can I return library books when the library is closed?",
        "gold_answer": "Dùng máy trả sách 24/7 ở cổng chính.",
        "answer_marker": "24/7-return-station",
        "metadata_filter": None,
    },
    {
        "query": "Sách Course Reserve được mượn bao lâu và phải trả ở đâu?",
        "english_query": "How long may Course Reserve books be used, and where are they returned?",
        "gold_answer": "Tối đa 2 giờ; mượn/trả tại Circulation Desk tầng 1.",
        "answer_marker": "Course reserves can be used in the library only for a maximum of two hours.",
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


def retrieve(store: EmbeddingStore, benchmark: dict) -> list[dict]:
    """Fuse Vietnamese and English rankings with Reciprocal Rank Fusion."""
    metadata_filter = benchmark["metadata_filter"]
    candidate_count = store.get_collection_size()
    merged: dict[str, dict] = {}
    for query in (benchmark["query"], benchmark["english_query"]):
        for rank, result in enumerate(
            store.search_with_filter(query, top_k=candidate_count, metadata_filter=metadata_filter),
            start=1,
        ):
            existing = merged.get(result["id"])
            rrf_score = 1 / (60 + rank)
            if existing is None:
                merged[result["id"]] = {**result, "score": rrf_score}
            else:
                existing["score"] += rrf_score
    return sorted(merged.values(), key=lambda result: result["score"], reverse=True)[:3]


def contains_answer_marker(content: str, marker: str) -> bool:
    """Compare content robustly when Markdown tables have variable whitespace."""
    normalize = lambda text: " ".join(text.lower().split())
    return normalize(marker) in normalize(content)


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
        results = retrieve(store, benchmark)
        print(f"\n[{number}] {benchmark['query']}")
        print(f"Gold: {benchmark['gold_answer']}")
        print(f"Filter: {metadata_filter or 'none'}")
        print(f"English expansion: {benchmark['english_query']}")
        marker_rank = next(
            (rank for rank, result in enumerate(results, start=1) if contains_answer_marker(result["content"], benchmark["answer_marker"])),
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
        results = retrieve(store, {**benchmark, "metadata_filter": metadata_filter})
        print(f"{label}:")
        for rank, result in enumerate(results, start=1):
            contains_marker = contains_answer_marker(result["content"], benchmark["answer_marker"])
            print(f"  {rank}. {result['metadata']['doc_id']} score={result['score']:.3f} marker={contains_marker}")


if __name__ == "__main__":
    main()
    run_filter_ab()
