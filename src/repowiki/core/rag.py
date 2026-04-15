"""lightweight TF-IDF retrieval for Q&A chat."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from repowiki.core.models import ProjectContext


@dataclass
class Chunk:
    file_path: str
    line_start: int
    line_end: int
    content: str
    score: float = 0.0


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

        self._idf = {
            token: math.log(doc_count / (count + 1))
            for token, count in df.items()
        }

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


def _tokenize(text: str) -> list[str]:
    """split text into lowercase tokens, keeping identifiers intact."""
    # split on non-alphanumeric, underscore preserved
    tokens = re.findall(r"[a-zA-Z_]\w*", text.lower())
    return tokens


def _cosine_similarity(
    vec_a: Counter, vec_b: Counter, idf: dict[str, float]
) -> float:
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
        is_boundary = (line.strip() == "" and len(current_lines) >= 5)
        is_too_long = len(current_lines) >= max_chunk_lines

        if is_boundary or is_too_long or i == len(lines) - 1:
            if current_lines:
                content = "\n".join(current_lines)
                if content.strip():
                    chunks.append(Chunk(
                        file_path=file_path,
                        line_start=current_start + 1,
                        line_end=current_start + len(current_lines),
                        content=content,
                    ))
                current_start = i + 1
                current_lines = []

    return chunks
