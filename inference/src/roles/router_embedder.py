"""[PRODUCTION] Embedder của router nhánh C — chạy trong image ai-inference.

Port NGUYÊN THUẬT TOÁN của ``SemanticDenseEmbedder.transform_single``
(``ai-service/src/ai/inference/embedder.py``), đọc bảng IDF từ ``artifacts/router_embedder.json``
(xuất bởi ``scripts/export_router_embedder.py``). Không cần ``joblib`` và không cần code
ai-service — hai thứ image này không có, khiến ai-classify trước đây âm thầm bỏ qua mô hình.

Đây là feature hashing n-gram ký tự + IDF, KHÔNG phải vector ngữ nghĩa BGE-M3.
Mọi thay đổi ở đây phải giữ test parity ``inference/tests/test_router_embedder_parity.py`` xanh:
lệch một bit trong cách băm là router nhận vector khác lúc huấn luyện mà không lỗi nào báo ra.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np

_WORD = re.compile(r"\w+")


def extract_subword_tokens(text: str) -> list[str]:
    """Từ + n-gram ký tự 3 và 4 của mỗi từ — giống hệt bản huấn luyện."""
    words = _WORD.findall(text.lower().strip())
    tokens: list[str] = list(words)
    for w in words:
        if len(w) >= 3:
            tokens.extend(w[i : i + 3] for i in range(len(w) - 2))
        if len(w) >= 4:
            tokens.extend(w[i : i + 4] for i in range(len(w) - 3))
    return tokens


class RouterEmbedder:
    def __init__(self, dim: int, n_docs: int, idf: dict[str, float], classes: list[str]) -> None:
        self.dim = dim
        self.n_docs = n_docs
        self.idf = idf
        self.classes = classes
        self._default_idf = float(np.log(n_docs + 1) + 1.0) if n_docs > 0 else 1.0

    @classmethod
    def from_json(cls, path: str | Path) -> RouterEmbedder:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != "router-embedder/v1":
            raise ValueError(f"{path}: định dạng {data.get('format')!r} không được hỗ trợ")
        return cls(int(data["dim"]), int(data["n_docs"]), data["idf"], list(data["classes"]))

    def transform_single(self, text: str) -> np.ndarray:
        tokens = extract_subword_tokens(text) or ["<pad>"]
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in tokens:
            w = self.idf.get(tok, self._default_idf)
            raw = tok.encode("utf-8")
            h1 = int(hashlib.md5(raw).hexdigest(), 16) % self.dim
            h2 = int(hashlib.sha1(raw).hexdigest(), 16) % self.dim
            sign = 1.0 if h1 % 2 == 0 else -1.0
            vec[h1] += sign * w
            vec[h2] += sign * 0.5 * w
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
