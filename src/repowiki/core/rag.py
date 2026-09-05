"""lightweight TF-IDF retrieval for Q&A chat."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from repowiki.core.models import ProjectContext

_INDEX_DIR = Path.home() / ".repowiki" / "rag"


@dataclass
class Chunk:
    file_path: str
    line_start: int
    line_end: int
    content: str
    score: float = 0.0


def index_fingerprint(project: ProjectContext) -> str:
    """Hash of the repo root plus every indexed file's path, size, and content.

    Any edit, add, or delete under the repo changes the fingerprint, so a stale
    index on disk simply never matches.
    """
    h = hashlib.sha256()
    h.update(str(Path(project.root).resolve()).encode())
    for f in sorted(project.files, key=lambda x: x.path):
        text = f.content or f.preview
        h.update(f.path.encode())
        h.update(str(f.size).encode())
        h.update(hashlib.sha256(text.encode()).digest())
    return h.hexdigest()[:24]


class SimpleRAG:
    """TF-IDF based code retrieval, no external dependencies."""

    def __init__(self):
        self.chunks: list[Chunk] = []
        self._idf: dict[str, float] = {}
        self._tf_vectors: list[Counter] = []

    def index(self, project: ProjectContext) -> None:
        """chunk project files and build the TF-IDF index."""
        self.chunks = []
        for f in project.files:
            text = f.content or f.preview
            if not text:
                continue
            file_chunks = _split_into_chunks(text, f.path)
            self.chunks.extend(file_chunks)

        # build IDF
        doc_count = len(self.chunks)
        if doc_count == 0:
            return

        df: Counter = Counter()
        self._tf_vectors = []

        for chunk in self.chunks:
            tokens = _tokenize(chunk.content)
            tf = Counter(tokens)
            self._tf_vectors.append(tf)
            for token in set(tokens):
                df[token] += 1

        self._idf = {token: math.log(doc_count / (count + 1)) for token, count in df.items()}

    def save_index(self, path: Path) -> None:
        """Persist chunks and vectors as JSON; written atomically so a
        half-written file never reads back as a valid index."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [
                {
                    "file_path": c.file_path,
                    "line_start": c.line_start,
                    "line_end": c.line_end,
                    "content": c.content,
                }
                for c in self.chunks
            ],
            "idf": self._idf,
            "tf_vectors": [dict(tf) for tf in self._tf_vectors],
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load_index(cls, path: Path) -> SimpleRAG | None:
        """Read back a saved index; any corruption is treated as a cache miss."""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rag = cls()
            rag.chunks = [Chunk(**c) for c in payload["chunks"]]
            rag._idf = {t: float(v) for t, v in payload["idf"].items()}
            rag._tf_vectors = [Counter(tf) for tf in payload["tf_vectors"]]
            if len(rag.chunks) != len(rag._tf_vectors):
                return None
            return rag
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        """find top-k chunks most relevant to the query."""
        if not self.chunks:
            return []

        query_tokens = _tokenize(query)
        query_tf = Counter(query_tokens)

        scores = []
        for i, chunk in enumerate(self.chunks):
            tf_vec = self._tf_vectors[i]
            score = _cosine_similarity(query_tf, tf_vec, self._idf)
            scores.append((score, i))

        scores.sort(reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            if score <= 0:
                break
            chunk = self.chunks[idx]
            chunk.score = score
            results.append(chunk)

        return results


def load_or_build_index(
    project: ProjectContext, index_dir: str | Path | None = None
) -> tuple[SimpleRAG, bool]:
    """Load a persisted index for an unchanged repo, else build and save one.

    Returns (rag, cache_hit). One JSON file per repo fingerprint; a missing or
    mismatched file just means a rebuild.
    """
    index_dir = Path(index_dir) if index_dir is not None else _INDEX_DIR
    path = index_dir / f"{index_fingerprint(project)}.json"
    rag = SimpleRAG.load_index(path)
    if rag is not None and rag.chunks:
        return rag, True
    rag = SimpleRAG()
    rag.index(project)
    if rag.chunks:
        try:
            rag.save_index(path)
        except OSError:
            pass  # a cache that cannot be written should not break chat
    return rag, False


def format_context(chunks: list[Chunk]) -> str:
    """Render retrieved chunks into a prompt-ready context block.

    Each chunk becomes a fenced section labelled with its file path and line
    range, so the model can cite specific locations. Empty input yields a
    short placeholder rather than a blank prompt.
    """
    if not chunks:
        return "(no relevant code found in this repository)"
    blocks = []
    for c in chunks:
        blocks.append(
            f"### {c.file_path} (lines {c.line_start}-{c.line_end})\n```\n{c.content}\n```"
        )
    return "\n\n".join(blocks)


def _tokenize(text: str) -> list[str]:
    """split text into lowercase tokens, keeping identifiers intact."""
    # split on non-alphanumeric, underscore preserved
    tokens = re.findall(r"[a-zA-Z_]\w*", text.lower())
    return tokens


def _cosine_similarity(vec_a: Counter, vec_b: Counter, idf: dict[str, float]) -> float:
    """TF-IDF weighted cosine similarity."""
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0

    dot = sum(vec_a[t] * idf.get(t, 0) * vec_b[t] * idf.get(t, 0) for t in common)
    norm_a = math.sqrt(sum((vec_a[t] * idf.get(t, 0)) ** 2 for t in vec_a))
    norm_b = math.sqrt(sum((vec_b[t] * idf.get(t, 0)) ** 2 for t in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _split_into_chunks(text: str, file_path: str, max_chunk_lines: int = 30) -> list[Chunk]:
    """split file content into chunks at blank line boundaries."""
    lines = text.splitlines()
    chunks = []
    current_start = 0
    current_lines: list[str] = []

    for i, line in enumerate(lines):
        current_lines.append(line)

        # split at blank lines or when chunk gets too large
        is_boundary = line.strip() == "" and len(current_lines) >= 5
        is_too_long = len(current_lines) >= max_chunk_lines

        if is_boundary or is_too_long or i == len(lines) - 1:
            if current_lines:
                content = "\n".join(current_lines)
                if content.strip():
                    chunks.append(
                        Chunk(
                            file_path=file_path,
                            line_start=current_start + 1,
                            line_end=current_start + len(current_lines),
                            content=content,
                        )
                    )
                current_start = i + 1
                current_lines = []

    return chunks
