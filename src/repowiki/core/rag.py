"""lightweight hybrid retrieval (TF-IDF + BM25) for Q&A chat.

Tokenization is identifier-aware: ``getUserById`` and ``is_authenticated``
are also indexed under their constituent sub-words so a query for
``user`` finds the camelCase getter, and ``auth`` finds the snake_case
predicate. A small stopword list trims code-noise words that otherwise
dominate the IDF tail.

Chunking respects language-specific section starts (def/class/function/
func/fn/method declarations) where possible, with a hard 60-line cap and
a small overlap between adjacent chunks so a reference straddling the
boundary is still recoverable. Wiki markdown is sliced separately by
heading sections so a question about the architecture page can hit the
wiki text directly rather than only the source files behind it.

Retrieval combines TF-IDF cosine similarity with BM25 scoring and
normalises both to ``[0, 1]`` before averaging. This keeps the
zero-dependency posture of the original TF-IDF retriever while picking
up BM25's better behaviour on long/short documents.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from repowiki.core.models import ProjectContext

# Stop words tailored for source code: language keywords + universally
# common English words that drown out signal in the IDF tail.
_STOPWORDS: frozenset[str] = frozenset(
    {
        # English filler
        "a", "an", "and", "as", "at", "be", "by", "for", "from", "has",
        "have", "in", "is", "it", "its", "of", "on", "or", "that", "the",
        "this", "to", "was", "with",
        # control flow / common keywords
        "if", "else", "elif", "while", "for", "return", "yield", "break",
        "continue", "pass", "in", "not", "and", "or", "is", "true", "false",
        "none", "null", "void", "new", "var", "let", "const", "this",
        "self", "super", "try", "except", "catch", "finally", "throw",
        "throws", "raise", "with", "as", "import", "from", "use", "using",
        "package", "module", "namespace", "type", "interface", "enum",
        "struct", "trait", "impl", "fn", "func", "function", "def", "class",
        "public", "private", "protected", "static", "final", "abstract",
        "override", "async", "await",
    }
)

# Section-start patterns by language. Each pattern matches a line *start*
# that we treat as a natural chunk boundary.
_SECTION_START_RAW: dict[str, list[str]] = {
    "python": [
        r"^\s*(?:async\s+)?def\s+",
        r"^\s*class\s+",
        r"^\s*@\w",  # decorator above a def is a fine cut point too
    ],
    "javascript": [
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+",
        r"^\s*(?:export\s+)?class\s+",
        r"^\s*(?:export\s+)?const\s+\w+\s*=\s*(?:async\s*)?\(",
    ],
    "typescript": [],  # filled in below from javascript
    "go": [r"^\s*func\s+"],
    "rust": [
        r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+",
        r"^\s*impl\s+",
        r"^\s*struct\s+",
        r"^\s*enum\s+",
    ],
    "java": [r"^\s*(?:public|private|protected)\s+"],
    "kotlin": [
        r"^\s*(?:public|private|internal)?\s*fun\s+",
        r"^\s*class\s+",
    ],
}
# typescript shares js patterns + a few extras
_SECTION_START_RAW["typescript"] = _SECTION_START_RAW["javascript"] + [
    r"^\s*(?:export\s+)?interface\s+",
    r"^\s*(?:export\s+)?type\s+\w+\s*=",
]
# common aliases
for _alias_src, _alias_dsts in (
    ("javascript", ("jsx", "mjs", "cjs")),
    ("typescript", ("tsx",)),
):
    for _d in _alias_dsts:
        _SECTION_START_RAW[_d] = _SECTION_START_RAW[_alias_src]

_SECTION_START: dict[str, list[re.Pattern[str]]] = {
    lang: [re.compile(p) for p in pats]
    for lang, pats in _SECTION_START_RAW.items()
}


@dataclass
class Chunk:
    file_path: str
    line_start: int
    line_end: int
    content: str
    # ``code`` for source-file chunks, ``wiki`` for slices of generated
    # wiki markdown. The retrieval scorer is identical for both, but the
    # caller can prefer or annotate one over the other.
    kind: str = "code"
    score: float = 0.0


class SimpleRAG:
    """hybrid (TF-IDF + BM25) code retrieval, no external dependencies."""

    # Bumped when the on-disk schema changes; see ``rag_store.SCHEMA_VERSION``.
    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        k1: float = 1.5,
        b: float = 0.75,
        max_chunk_lines: int = 60,
        soft_chunk_lines: int = 30,
        overlap_lines: int = 5,
    ):
        self.chunks: list[Chunk] = []
        self._idf: dict[str, float] = {}
        self._tf_vectors: list[Counter] = []
        # BM25 needs per-chunk lengths and the corpus mean.
        self._chunk_lens: list[int] = []
        self._avgdl: float = 0.0
        # BM25 tuning. The defaults are the classic values; expose them so
        # large/small repos can be retuned via Config without code changes.
        self._k1 = float(k1)
        self._b = float(b)
        # Chunking config retained on the instance so persistence + chat
        # paths use the same numbers we indexed with.
        self.max_chunk_lines = int(max_chunk_lines)
        self.soft_chunk_lines = int(soft_chunk_lines)
        self.overlap_lines = int(overlap_lines)
        # Incremental bookkeeping: which chunk indices belong to each file
        # and the content hash we indexed last (so callers can skip files
        # that didn't change).
        self._file_to_chunks: dict[str, list[int]] = {}
        self._file_sha: dict[str, str] = {}

    # ---------- bulk + incremental indexing ----------

    def index(self, project: ProjectContext) -> None:
        """chunk every project file and build the global statistics.

        Existing callers (the CLI ``chat`` command and the server's
        background preheat) get the original "from scratch" behaviour.
        """
        self.chunks = []
        self._file_to_chunks = {}
        self._file_sha = {}
        for f in project.files:
            text = f.content or f.preview
            if not text:
                continue
            self.upsert_file(
                f.path,
                sha=_fast_sha(text),
                language=f.language,
                text=text,
                kind="code",
                rebuild=False,
            )
        self.rebuild_global()

    def upsert_file(
        self,
        path: str,
        sha: str,
        language: str,
        text: str,
        kind: str = "code",
        *,
        rebuild: bool = True,
    ) -> None:
        """add or replace a file's chunks in the index.

        When the same path is already indexed we drop its previous chunks
        first so the new ones cleanly replace them. Pass ``rebuild=False``
        to defer the global IDF/avgdl recompute (useful when upserting
        many files in a row).
        """
        if path in self._file_to_chunks:
            self.remove_file(path, rebuild=False)

        new_chunks = _chunk_for_kind(
            text,
            path,
            language,
            kind=kind,
            max_chunk_lines=self.max_chunk_lines,
            soft_chunk_lines=self.soft_chunk_lines,
            overlap_lines=self.overlap_lines,
        )
        if not new_chunks:
            self._file_sha[path] = sha
            return

        indices: list[int] = []
        for chunk in new_chunks:
            idx = len(self.chunks)
            self.chunks.append(chunk)
            tokens = _tokenize(chunk.content)
            self._tf_vectors.append(Counter(tokens))
            self._chunk_lens.append(max(1, len(tokens)))
            indices.append(idx)

        self._file_to_chunks[path] = indices
        self._file_sha[path] = sha

        if rebuild:
            self.rebuild_global()

    def remove_file(self, path: str, *, rebuild: bool = True) -> None:
        """drop every chunk that belongs to ``path``.

        We rebuild the chunk array rather than punching holes, because the
        BM25 / TF-IDF passes both need ``self.chunks`` and
        ``self._tf_vectors`` to stay index-aligned.
        """
        indices = self._file_to_chunks.pop(path, None)
        self._file_sha.pop(path, None)
        if not indices:
            return

        drop = set(indices)
        kept_chunks: list[Chunk] = []
        kept_tf: list[Counter] = []
        kept_lens: list[int] = []
        # Map old chunk index -> new index so we can rewrite the
        # per-file bookkeeping for the files we kept.
        remap: dict[int, int] = {}
        for old_idx, chunk in enumerate(self.chunks):
            if old_idx in drop:
                continue
            remap[old_idx] = len(kept_chunks)
            kept_chunks.append(chunk)
            kept_tf.append(self._tf_vectors[old_idx])
            kept_lens.append(self._chunk_lens[old_idx])

        self.chunks = kept_chunks
        self._tf_vectors = kept_tf
        self._chunk_lens = kept_lens
        # Rewire surviving files' chunk-index lists.
        for other_path, idxs in self._file_to_chunks.items():
            self._file_to_chunks[other_path] = [remap[i] for i in idxs if i in remap]

        if rebuild:
            self.rebuild_global()

    def rebuild_global(self) -> None:
        """recompute IDF and avgdl after a batch of upserts/removes."""
        doc_count = len(self.chunks)
        if doc_count == 0:
            self._idf = {}
            self._avgdl = 0.0
            return

        df: Counter = Counter()
        for tf in self._tf_vectors:
            for token in tf:
                df[token] += 1

        # Smoothed IDF (sklearn-style): always > 0 even when a term appears
        # in every document, and remains finite on tiny corpora.
        self._idf = {
            token: math.log((doc_count + 1) / (count + 1)) + 1.0
            for token, count in df.items()
        }
        self._avgdl = sum(self._chunk_lens) / doc_count

    # ---------- retrieval ----------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        *,
        min_score: float = 0.0,
    ) -> list[Chunk]:
        """find top-k chunks most relevant to ``query``.

        Score is the average of TF-IDF cosine similarity and BM25, each
        normalised to ``[0, 1]`` by dividing by their respective max
        across the corpus. The single-score view makes ``min_score``
        meaningful regardless of corpus size.
        """
        if not self.chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        query_tf = Counter(query_tokens)

        n = len(self.chunks)
        tfidf_scores = [0.0] * n
        bm25_scores = [0.0] * n
        for i in range(n):
            tf_vec = self._tf_vectors[i]
            tfidf_scores[i] = _cosine_similarity(query_tf, tf_vec, self._idf)
            bm25_scores[i] = _bm25(
                query_tokens, tf_vec, self._chunk_lens[i],
                self._idf, self._avgdl, self._k1, self._b,
            )

        max_tfidf = max(tfidf_scores) if tfidf_scores else 0.0
        max_bm25 = max(bm25_scores) if bm25_scores else 0.0

        fused: list[tuple[float, int]] = []
        for i in range(n):
            tfidf_n = tfidf_scores[i] / max_tfidf if max_tfidf > 0 else 0.0
            bm25_n = bm25_scores[i] / max_bm25 if max_bm25 > 0 else 0.0
            fused.append(((tfidf_n + bm25_n) / 2.0, i))

        fused.sort(reverse=True)
        results: list[Chunk] = []
        for score, idx in fused[:top_k]:
            if score <= 0 or score < min_score:
                break
            chunk = self.chunks[idx]
            chunk.score = score
            results.append(chunk)
        return results

    # ---------- wiki indexing helper ----------

    def index_wiki_pages(self, pages: list) -> None:
        """slice generated wiki markdown into chunks and add them.

        ``pages`` is a list of objects with ``id`` and ``content`` (a
        :class:`repowiki.core.wiki_builder.WikiPage` works). Existing wiki
        chunks are dropped first so re-running ``scan`` doesn't double-index
        the same page.
        """
        # Wipe any prior wiki chunks (keyed by their virtual paths).
        to_remove = [p for p in list(self._file_to_chunks) if p.startswith("wiki/")]
        for p in to_remove:
            self.remove_file(p, rebuild=False)

        for page in pages:
            content = getattr(page, "content", "") or ""
            page_id = getattr(page, "id", "") or "page"
            if not content.strip():
                continue
            virtual_path = f"wiki/{page_id}.md"
            self.upsert_file(
                virtual_path,
                sha=_fast_sha(content),
                language="markdown",
                text=content,
                kind="wiki",
                rebuild=False,
            )
        self.rebuild_global()


# ----- helpers (token / chunking / scoring) ---------------------------


_IDENT_RE = re.compile(r"[a-zA-Z_]\w*")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _split_identifier(token: str) -> list[str]:
    """yield sub-words for camelCase and snake_case identifiers.

    Always includes the original lowercased token so existing exact-match
    behaviour is preserved.
    """
    pieces: list[str] = [token.lower()]
    # snake_case
    if "_" in token:
        for p in token.split("_"):
            if p:
                pieces.append(p.lower())
    # camelCase / PascalCase
    camel_parts = _CAMEL_BOUNDARY.split(token)
    if len(camel_parts) > 1:
        for p in camel_parts:
            if p:
                pieces.append(p.lower())
    return pieces


def _tokenize(text: str) -> list[str]:
    """split text into lowercase tokens, also emitting camelCase/snake_case
    sub-words. Stopwords are filtered.
    """
    out: list[str] = []
    for raw in _IDENT_RE.findall(text):
        for piece in _split_identifier(raw):
            if len(piece) < 2:
                continue
            if piece in _STOPWORDS:
                continue
            out.append(piece)
    return out


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


def _bm25(
    query_tokens: list[str],
    tf_vec: Counter,
    chunk_len: int,
    idf: dict[str, float],
    avgdl: float,
    k1: float,
    b: float,
) -> float:
    """BM25 score for a single document.

    Uses the same IDF table as the TF-IDF cosine path (smoothed), which
    keeps both scorers consistent without a second pass over the corpus.
    """
    if avgdl <= 0:
        return 0.0
    score = 0.0
    norm = (1.0 - b) + b * (chunk_len / avgdl)
    for token in set(query_tokens):
        if token not in idf:
            continue
        f = tf_vec.get(token, 0)
        if f == 0:
            continue
        score += idf[token] * f * (k1 + 1.0) / (f + k1 * norm)
    return score


def _chunk_for_kind(
    text: str,
    file_path: str,
    language: str,
    *,
    kind: str,
    max_chunk_lines: int,
    soft_chunk_lines: int,
    overlap_lines: int,
) -> list[Chunk]:
    """dispatch to the right chunker and tag the chunks with ``kind``."""
    if kind == "wiki":
        chunks = _split_markdown_into_chunks(
            text, file_path, max_lines=max_chunk_lines,
        )
    else:
        chunks = _split_into_chunks(
            text,
            file_path,
            language=language,
            max_chunk_lines=max_chunk_lines,
            soft_chunk_lines=soft_chunk_lines,
            overlap_lines=overlap_lines,
        )
    for c in chunks:
        c.kind = kind
    return chunks


def _split_into_chunks(
    text: str,
    file_path: str,
    language: str = "",
    max_chunk_lines: int = 60,
    soft_chunk_lines: int = 30,
    overlap_lines: int = 5,
) -> list[Chunk]:
    """split file content into chunks.

    Strategy:
      1. Detect language-specific *section starts* (def/class/function/etc.)
         and prefer to begin a chunk there.
      2. Allow up to ``soft_chunk_lines`` of slop before we look for a
         section start; once we exceed ``max_chunk_lines`` we cut hard.
      3. Carry the trailing ``overlap_lines`` of each chunk into the next,
         so a reference straddling a boundary still appears in both.

    Falls back to the original blank-line heuristic for languages we don't
    recognize.
    """
    lines = text.splitlines()
    if not lines:
        return []

    section_patterns = _SECTION_START.get(language)
    if not section_patterns:
        return _split_by_blank_lines(lines, file_path, max_lines=soft_chunk_lines)

    chunks: list[Chunk] = []
    current_start = 0
    current: list[str] = []

    def _flush(start_idx: int, buf: list[str]) -> None:
        """emit the current chunk if it has content."""
        if not buf:
            return
        joined = "\n".join(buf)
        if joined.strip():
            chunks.append(
                Chunk(
                    file_path=file_path,
                    line_start=start_idx + 1,
                    line_end=start_idx + len(buf),
                    content=joined,
                )
            )

    def _is_section_start(line: str) -> bool:
        return any(p.search(line) for p in section_patterns)

    for i, line in enumerate(lines):
        # treat a section start as a cut point if we already have at least
        # soft_chunk_lines accumulated. This keeps decorators glued to their
        # def, and short helper clusters grouped together.
        if (
            _is_section_start(line)
            and len(current) >= soft_chunk_lines
        ):
            _flush(current_start, current)
            tail = current[-overlap_lines:] if overlap_lines else []
            # next chunk starts at the overlap window, not at i
            current_start = i - len(tail)
            current = list(tail)

        current.append(line)

        # hard cap: even mid-function we must break
        if len(current) >= max_chunk_lines:
            _flush(current_start, current)
            tail = current[-overlap_lines:] if overlap_lines else []
            current_start = i + 1 - len(tail)
            current = list(tail)

    _flush(current_start, current)
    return chunks


def _split_by_blank_lines(
    lines: list[str], file_path: str, max_lines: int = 30
) -> list[Chunk]:
    """fallback chunker -- original blank-line heuristic.

    Used for languages we don't have section-start patterns for.
    """
    chunks: list[Chunk] = []
    current_start = 0
    current_lines: list[str] = []
    for i, line in enumerate(lines):
        current_lines.append(line)
        is_boundary = line.strip() == "" and len(current_lines) >= 5
        is_too_long = len(current_lines) >= max_lines
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


_HEADING_RE = re.compile(r"^#{1,6}\s+")


def _split_markdown_into_chunks(
    text: str, file_path: str, *, max_lines: int = 60
) -> list[Chunk]:
    """slice markdown into chunks by heading sections.

    Each ``#`` / ``##`` / ... heading starts a new chunk. If a single
    section exceeds ``max_lines`` it's split again at the heading-less
    line cap so a long page doesn't become one giant chunk.
    """
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[Chunk] = []
    section_start = 0
    section_lines: list[str] = []

    def _flush_section() -> None:
        if not section_lines:
            return
        # Inside a section, split further if it exceeds the line cap.
        for offset in range(0, len(section_lines), max_lines):
            piece = section_lines[offset : offset + max_lines]
            joined = "\n".join(piece).strip()
            if not joined:
                continue
            chunks.append(
                Chunk(
                    file_path=file_path,
                    line_start=section_start + offset + 1,
                    line_end=section_start + offset + len(piece),
                    content="\n".join(piece),
                )
            )

    for i, line in enumerate(lines):
        if _HEADING_RE.match(line) and section_lines:
            _flush_section()
            section_start = i
            section_lines = [line]
        else:
            section_lines.append(line)

    _flush_section()
    return chunks


def _fast_sha(text: str) -> str:
    """short content hash for incremental staleness checks.

    Mirrors :func:`repowiki.core.cache.content_hash` (sha256 -> 24 chars)
    so the analyzer cache and the RAG index can share the same digest of a
    file body without re-hashing it twice.
    """
    import hashlib
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:24]
