"""Optional retrieval: chunk documents, embed them, store the vectors, find the closest chunks.

Everything here is pure Python on purpose (D-002): `HashingEmbedder` is the retrieval
counterpart of the fake model, deterministic and free, so retrieval code and its evals run
without a key or a GPU. Real embeddings come from `LiteLLMEmbedder` (the litellm extra), or
from any object that satisfies the `Embedder` port. `InMemoryVectorStore` is a brute-force
cosine search, fine for thousands of chunks; a database-backed store satisfies `VectorStore`.
"""

import math
import re
import zlib
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

Vector = list[float]
WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by for from has have how i in is it of on or that the this to was "
    "what when where which who why will with you your".split()
)


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> list[Vector]:
        """One vector per text, all of the same dimension."""
        ...


class VectorStore(Protocol):
    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Vector]) -> None: ...

    def search(self, vector: Vector, k: int) -> list[ScoredChunk]: ...


def chunk_text(text: str, doc_id: str, *, max_chars: int = 800, overlap: int = 100) -> list[Chunk]:
    """Split on blank lines and pack paragraphs into chunks of at most ``max_chars``.

    A paragraph longer than ``max_chars`` is cut into windows that overlap by ``overlap``
    characters, so a sentence on a boundary is still found whole in one of them.
    """
    if max_chars <= overlap:
        raise ValueError("max_chars must be larger than overlap")
    pieces: list[str] = []
    for paragraph in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
            continue
        step = max_chars - overlap
        for start in range(0, len(paragraph), step):
            pieces.append(paragraph[start : start + max_chars])
            if start + max_chars >= len(paragraph):
                break
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 2 + len(piece) <= max_chars:
            chunks[-1] = f"{chunks[-1]}\n\n{piece}"
        else:
            chunks.append(piece)
    return [Chunk(id=f"{doc_id}#{i}", doc_id=doc_id, text=c) for i, c in enumerate(chunks)]


def tokenize(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS]


def _normalize(vector: Vector) -> Vector:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else vector


class HashingEmbedder:
    """Deterministic lexical embedding: each word is hashed into one of ``dimension``
    buckets with weight 1 + log(count), and the vector is L2-normalized. It finds texts that
    share words, not texts that share meaning; use a real embedder for that."""

    def __init__(self, dimension: int = 1024) -> None:
        self.dimension = dimension

    def embed(self, texts: Sequence[str]) -> list[Vector]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimension
            for word, count in Counter(tokenize(text)).items():
                # crc32, not hash(): Python salts str hashes per process.
                vector[zlib.crc32(word.encode()) % self.dimension] += 1.0 + math.log(count)
            vectors.append(_normalize(vector))
        return vectors


class LiteLLMEmbedder:
    """Embeddings from any LiteLLM model (install the ``litellm`` extra)."""

    def __init__(self, model: str, **defaults: Any) -> None:
        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError(
                "LiteLLMEmbedder needs the litellm extra: pip install 'ai-app-chassis[litellm]'"
            ) from exc
        self._litellm = litellm
        self.model = model
        self._defaults = defaults

    def embed(self, texts: Sequence[str]) -> list[Vector]:
        response = self._litellm.embedding(model=self.model, input=list(texts), **self._defaults)
        # LiteLLM returns plain dicts for some providers and Embedding objects for others.
        vectors = [i["embedding"] if isinstance(i, dict) else i.embedding for i in response.data]
        return [_normalize([float(x) for x in vector]) for vector in vectors]


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[Vector] = []

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Vector]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")
        self._chunks.extend(chunks)
        self._vectors.extend(_normalize(list(v)) for v in vectors)

    def search(self, vector: Vector, k: int) -> list[ScoredChunk]:
        query = _normalize(list(vector))
        if not any(query):
            return []
        scored = [
            ScoredChunk(chunk, sum(a * b for a, b in zip(query, stored, strict=True)))
            for chunk, stored in zip(self._chunks, self._vectors, strict=True)
        ]
        # sorted() is stable, so equal scores keep insertion order: results are reproducible.
        ranked = sorted(scored, key=lambda s: s.score, reverse=True)
        return [s for s in ranked if s.score > 0][:k]


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore | None = None,
        *,
        max_chars: int = 800,
        overlap: int = 100,
    ) -> None:
        self.embedder = embedder
        self.store: VectorStore = store if store is not None else InMemoryVectorStore()
        self._max_chars = max_chars
        self._overlap = overlap

    def index(self, documents: Mapping[str, str]) -> int:
        """Chunk, embed and store ``{doc_id: text}``; returns the number of chunks added."""
        chunks = [
            chunk
            for doc_id, text in documents.items()
            for chunk in chunk_text(text, doc_id, max_chars=self._max_chars, overlap=self._overlap)
        ]
        if chunks:
            self.store.add(chunks, self.embedder.embed([c.text for c in chunks]))
        return len(chunks)

    def retrieve(self, query: str, k: int = 5) -> list[ScoredChunk]:
        [vector] = self.embedder.embed([query])
        return self.store.search(vector, k)

    def retrieve_documents(self, query: str, k: int = 5) -> list[str]:
        """Distinct document ids in rank order, from the best chunk of each document."""
        seen: list[str] = []
        for scored in self.retrieve(query, k * 4):
            if scored.chunk.doc_id not in seen:
                seen.append(scored.chunk.doc_id)
        return seen[:k]


def recall_at_k(ranked: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Share of the relevant ids found in the first ``k`` results."""
    wanted = set(relevant)
    return len(wanted & set(ranked[:k])) / len(wanted) if wanted else 1.0


def reciprocal_rank(ranked: Sequence[str], relevant: Iterable[str]) -> float:
    """1 / rank of the first relevant result, 0 when none was retrieved."""
    wanted = set(relevant)
    return next((1.0 / (i + 1) for i, item in enumerate(ranked) if item in wanted), 0.0)
