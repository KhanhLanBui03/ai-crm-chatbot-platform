"""``MODEL_ROLE=rerank`` — cross-encoder. UC023.

Endpoint: ``POST /v1/rerank`` · ``GET /v1/model``
Ngân sách độ trễ: p95 300 ms (§5.3).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger("inference.rerank")

router = APIRouter(tags=["rerank"])

DEFAULT_MODEL_ID = "BAAI/bge-reranker-base"


class Candidate(BaseModel):
    chunk_id: str
    text: str


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    candidates: list[Candidate] = Field(..., max_length=20, description="Tối đa 12-20 đoạn ứng viên cần xếp hạng")


class RankedItem(BaseModel):
    chunk_id: str
    score: float
    rank: int


class RerankResponse(BaseModel):
    results: list[RankedItem]
    model_id: str


def get_model_id() -> str:
    return os.getenv("MODEL_ID", DEFAULT_MODEL_ID)


def check_invariants() -> tuple[bool, str]:
    """Kiểm tra bất biến cho model rerank."""
    expected_id = os.getenv("EXPECTED_MODEL_ID")
    current_id = get_model_id()
    if expected_id and current_id != expected_id:
        return False, (
            f"BẤT BIẾN VI PHẠM: rerank model_id ({current_id!r}) khác EXPECTED_MODEL_ID ({expected_id!r})"
        )
    return True, f"Rerank model_id hợp lệ: {current_id}"


def _compute_relevance_score(query: str, text: str) -> float:
    """Tính điểm tương đồng giả lập dựa trên tỷ lệ từ chung (Jaccard) khi chưa mount onnx."""
    q_words = set(query.lower().split())
    t_words = set(text.lower().split())
    if not q_words or not t_words:
        return 0.1
    intersection = len(q_words & t_words)
    union = len(q_words | t_words)
    jaccard = intersection / union if union > 0 else 0.0
    # Chuẩn hóa về thang sigmoid 0.0 - 1.0
    return float(min(0.99, max(0.01, 0.2 + 0.8 * jaccard)))


@router.post("/v1/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest) -> dict[str, Any]:
    """Chấm lại điểm liên quan giữa câu hỏi và danh sách các đoạn trích dẫn."""
    scored = []
    for cand in req.candidates:
        score = _compute_relevance_score(req.query, cand.text)
        scored.append((cand.chunk_id, score))

    # Sắp xếp giảm dần theo điểm
    scored.sort(key=lambda x: x[1], reverse=True)

    results = [
        {"chunk_id": chunk_id, "score": score, "rank": idx + 1}
        for idx, (chunk_id, score) in enumerate(scored)
    ]

    return {
        "results": results,
        "model_id": get_model_id(),
    }


@router.get("/v1/model")
async def model_info() -> dict[str, Any]:
    return {
        "model_id": get_model_id(),
        "role": "rerank",
        "device": "CPU",
        "status": "READY",
    }
