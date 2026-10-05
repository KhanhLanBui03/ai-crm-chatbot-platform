"""Bộ nhúng vector ngữ nghĩa (Semantic Dense Embedder) cho ai-embed và Router Nhánh C.

Mô phỏng không gian vector 1024 chiều chuẩn BAE-M3 / BGE-M3.
Đảm bảo tính tái lập (deterministic) và tính tương thích cao giữa tầng suy luận và huấn luyện.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

VECTOR_DIM = 1024


def extract_subword_tokens(text: str) -> list[str]:
    """Trích xuất từ đơn và n-gram ký tự con (subword n-grams) để nắm bắt biến thể."""
    text_clean = text.lower().strip()
    words = re.findall(r"\w+", text_clean)
    tokens: list[str] = list(words)
    for w in words:
        if len(w) >= 3:
            for i in range(len(w) - 2):
                tokens.append(w[i : i + 3])
        if len(w) >= 4:
            for i in range(len(w) - 3):
                tokens.append(w[i : i + 4])
    return tokens


class SemanticDenseEmbedder:
    """Mô phỏng bộ sinh vector dense 1024 chiều chuẩn BGE-M3 của ai-embed.
    
    Áp dụng kỹ thuật Feature Hashing đa băm kết hợp nghịch đảo tần số văn bản (IDF).
    Đảm bảo 100% deterministic (tái lập) và các câu cùng ngữ nghĩa có độ tương đồng cosine cao.
    """

    def __init__(self, dim: int = VECTOR_DIM):
        self.dim = dim
        self.idf: dict[str, float] = {}
        self.n_docs: int = 0

    def fit(self, texts: list[str]) -> SemanticDenseEmbedder:
        doc_counts: dict[str, int] = {}
        self.n_docs = len(texts)
        for text in texts:
            seen = set(extract_subword_tokens(text))
            for tok in seen:
                doc_counts[tok] = doc_counts.get(tok, 0) + 1
        
        self.idf = {
            tok: float(np.log((self.n_docs + 1) / (cnt + 1)) + 1.0)
            for tok, cnt in doc_counts.items()
        }
        return self

    def transform_single(self, text: str) -> np.ndarray:
        tokens = extract_subword_tokens(text)
        if not tokens:
            tokens = ["<pad>"]
        
        default_idf = float(np.log(self.n_docs + 1) + 1.0) if self.n_docs > 0 else 1.0
        vec = np.zeros(self.dim, dtype=np.float32)

        for tok in tokens:
            w = self.idf.get(tok, default_idf)
            h1 = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % self.dim
            h2 = int(hashlib.sha1(tok.encode("utf-8")).hexdigest(), 16) % self.dim
            sign = 1.0 if (h1 % 2 == 0) else -1.0
            vec[h1] += sign * w
            vec[h2] += sign * 0.5 * w

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def transform(self, texts: list[str]) -> np.ndarray:
        return np.array([self.transform_single(t) for t in texts], dtype=np.float32)
