"""A deterministic, offline embedding fallback.

This is intentionally small enough for a classroom MVP. Production deployments
should select an evaluated embedding model and rebuild the Chroma collection.
"""

from __future__ import annotations

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

TOKEN_RE = re.compile(r"[a-z0-9]+(?:\([a-z0-9]+\))*", re.IGNORECASE)


class HashingEmbeddings(Embeddings):
    """Signed feature-hashing embeddings with token and character features."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def _features(self, text: str) -> list[str]:
        tokens = TOKEN_RE.findall(text.lower())
        features = list(tokens)
        for token in tokens:
            if len(token) >= 5:
                padded = f"^{token}$"
                features.extend(padded[index : index + 3] for index in range(len(padded) - 2))
        return features

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            sign = 1.0 if (value >> 8) & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(component * component for component in vector))
        if norm:
            return [component / norm for component in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
