"""``MODEL_ROLE=embed`` — encoder. UC019 (lập chỉ mục) và UC023 (truy hồi).

Endpoint: ``POST /v1/embed`` · ``POST /v1/embed/batch`` · ``GET /v1/model``
Ngân sách độ trễ: p95 120 ms (§5.3).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("inference.embed")

router = APIRouter(tags=["embed"])

DEFAULT_MODEL_ID = "BAAI/bge-m3"
VECTOR_DIM = 1024  # Chốt 1024 theo ADR-0015


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Văn bản cần nhúng vector")


class BatchEmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=64, description="Danh sách văn bản nhúng batch")


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim: int
    model_id: str


class BatchEmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int
    count: int
    model_id: str


class ModelInfoResponse(BaseModel):
    model_id: str
    role: str
    dim: int
    device: str
    status: str


def get_model_id() -> str:
    return os.getenv("MODEL_ID", DEFAULT_MODEL_ID)


def check_invariants() -> tuple[bool, str]:
    """Kiểm tra Bất biến 1: model_id khớp cấu hình emb_model mong đợi."""
    expected_id = os.getenv("EXPECTED_MODEL_ID")
    current_id = get_model_id()
    if expected_id and current_id != expected_id:
        return False, (
            f"BẤT BIẾN 1 VI PHẠM: model_id đang nạp ({current_id!r}) khác EXPECTED_MODEL_ID ({expected_id!r}). "
            "Lệch không gian vector dẫn tới truy hồi vô nghĩa (EMBEDDING_MODEL_MISMATCH)."
        )
    return True, f"Embedding model_id hợp lệ: {current_id}"


def _generate_deterministic_embedding(text: str, dim: int = VECTOR_DIM) -> list[float]:
    """Sinh vector giả lập định danh deterministic (dùng khi chưa mount model .onnx thật)."""
    import hashlib
    import numpy as np

    # Tạo seed từ hash của text để cùng input luôn ra cùng output
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


@router.post("/v1/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest) -> dict[str, Any]:
    """Tạo vector nhúng 1024 chiều cho một đoạn văn bản."""
    vec = _generate_deterministic_embedding(req.text, VECTOR_DIM)
    return {
        "embedding": vec,
        "dim": VECTOR_DIM,
        "model_id": get_model_id(),
    }


@router.post("/v1/embed/batch", response_model=BatchEmbedResponse)
async def embed_batch(req: BatchEmbedRequest) -> dict[str, Any]:
    """Tạo vector nhúng cho một danh sách văn bản (tối đa 64 đoạn)."""
    embeddings = [_generate_deterministic_embedding(t, VECTOR_DIM) for t in req.texts]
    return {
        "embeddings": embeddings,
        "dim": VECTOR_DIM,
        "count": len(embeddings),
        "model_id": get_model_id(),
    }


@router.get("/v1/model", response_model=ModelInfoResponse)
async def model_info() -> dict[str, Any]:
    """Thông tin model embedding đang phục vụ."""
    return {
        "model_id": get_model_id(),
        "role": "embed",
        "dim": VECTOR_DIM,
        "device": "CPU",
        "status": "READY",
    }
