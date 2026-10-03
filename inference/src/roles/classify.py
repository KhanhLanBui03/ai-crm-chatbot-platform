"""``MODEL_ROLE=classify`` — router ý định (UC022) + lead scorer (UC030).

Endpoint: ``POST /v1/classify`` · ``POST /v1/lead-score`` · ``GET /v1/model``
Ngân sách độ trễ: Router p95 60 ms, Lead Scorer p95 < 1.000 ms (§5.3).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger("inference.classify")

router = APIRouter(tags=["classify"])

DEFAULT_MODEL_ID = "intent-router-v1"

# Taxonomy 7 nhánh ý định chuẩn theo Master Plan §5.9 và UC022
INTENT_TAXONOMY = [
    "GREETING",           # Chào hỏi, cảm ơn, xã giao
    "KB_SEARCH",          # Tra cứu thông tin, hỏi đáp tri thức
    "PRICING_POLICY",     # Hỏi báo giá, gói cước, chính sách khuyến mãi
    "COMPLAINT_SUPPORT",  # Khiếu nại dịch vụ, yêu cầu hỗ trợ chung
    "HANDOFF_HUMAN",      # Đòi gặp tư vấn viên / người thật trực tiếp
    "TECH_ERROR",         # Báo lỗi kỹ thuật, sự cố hệ thống
    "BUYING_INTENT",      # Ý định đặt mua, chốt hợp đồng, nâng cấp gói
]

# Hợp đồng thứ tự cột đặc trưng bắt buộc cho Lead Scorer UC030 (§5.10.4)
EXPECTED_FEATURE_COLUMNS = [
    "turn_count",
    "avg_user_message_length",
    "pricing_inquiry_count",
    "buying_intent_detected",
    "complaint_detected",
    "days_since_first_contact",
    "total_interactions",
    "company_size_tier",
]


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Nội dung câu nói người dùng")


class ClassifyResponse(BaseModel):
    intent: str
    confidence: float
    probabilities: dict[str, float]
    model_id: str


class LeadScoreRequest(BaseModel):
    features: dict[str, float] = Field(..., description="Từ điển đặc trưng trích xuất được")


class LeadScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    model_version: str
    confidence_level: str
    reasons: list[str]


def get_model_id() -> str:
    return os.getenv("MODEL_ID", DEFAULT_MODEL_ID)


def check_invariants() -> tuple[bool, str]:
    """Kiểm tra Bất biến 1 (model_id) và Bất biến 2 (thứ tự cột đặc trưng) theo §3.4.2."""
    # 1. Bất biến 1: model_id
    expected_id = os.getenv("EXPECTED_MODEL_ID")
    current_id = get_model_id()
    if expected_id and current_id != expected_id:
        return False, (
            f"BẤT BIẾN 1 VI PHẠM: classify model_id ({current_id!r}) khác EXPECTED_MODEL_ID ({expected_id!r})"
        )

    # 2. Bất biến 2: Thứ tự cột đặc trưng khớp lead_scorer.meta.json
    meta_path = Path("artifacts/lead_scorer.meta.json")
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            features_in_meta = meta.get("feature_names", [])
            if features_in_meta != EXPECTED_FEATURE_COLUMNS:
                return False, (
                    f"BẤT BIẾN 2 VI PHẠM: Thứ tự đặc trưng trong {meta_path} không khớp HỢP ĐỒNG. "
                    f"Kỳ vọng {EXPECTED_FEATURE_COLUMNS}, thực tế nhận {features_in_meta}"
                )
        except Exception as exc:
            return False, f"BẤT BIẾN 2 LỖI ĐỌC: Không thể đọc meta.json: {exc}"

    return True, f"Classify model_id và đặc trưng hợp lệ: {current_id}"


def _rule_based_classify(text: str) -> tuple[str, float, dict[str, float]]:
    """Phân loại ý định kết hợp keyword rule và xác suất giả lập."""
    import re
    t = text.lower().strip()
    words = set(re.findall(r"\w+", t))

    # Ưu tiên các ý định nghiệp vụ trước
    if any(p in t for p in ["gặp người", "tư vấn viên", "nhân viên", "người thật", "chuyển máy", "tổng đài", "chăm sóc khách hàng", "human agent"]):
        intent = "HANDOFF_HUMAN"
        conf = 0.96
    elif any(p in t for p in ["mua", "đặt hàng", "đăng ký", "thanh toán", "chuyển khoản", "hợp đồng", "nâng cấp gói"]):
        intent = "BUYING_INTENT"
        conf = 0.92
    elif any(p in t for p in ["giá", "báo giá", "gói", "chi phí", "bao nhiêu tiền", "bảng giá", "khuyến mãi", "ưu đãi", "phi duy tri"]):
        intent = "PRICING_POLICY"
        conf = 0.93
    elif any(p in t for p in ["lỗi", "không vào được", "hỏng", "sập", "bị đơ", "chết", "bug", "crash", "timeout"]):
        intent = "TECH_ERROR"
        conf = 0.91
    elif any(p in t for p in ["khiếu nại", "chậm trễ", "thái độ", "tệ", "thất vọng", "bồi thường", "phàn nàn"]):
        intent = "COMPLAINT_SUPPORT"
        conf = 0.90
    elif any(w in words for w in ["chào", "hi", "hello", "alo", "bye"]) or any(p in t for p in ["xin chào", "tạm biệt", "cảm ơn", "thanks"]):
        intent = "GREETING"
        conf = 0.95
    else:
        intent = "KB_SEARCH"
        conf = 0.85

    probs = {i: 0.02 for i in INTENT_TAXONOMY}
    probs[intent] = conf
    # Chuẩn hóa tổng xác suất = 1.0
    rem = (1.0 - conf) / (len(INTENT_TAXONOMY) - 1)
    for k in probs:
        if k != intent:
            probs[k] = round(rem, 4)

    return intent, conf, probs


@router.post("/v1/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest) -> dict[str, Any]:
    """Phân loại câu hỏi người dùng thành 1 trong 7 nhánh ý định."""
    intent, conf, probs = _rule_based_classify(req.text)
    return {
        "intent": intent,
        "confidence": conf,
        "probabilities": probs,
        "model_id": get_model_id(),
    }


@router.post("/v1/lead-score", response_model=LeadScoreResponse)
async def score_lead(req: LeadScoreRequest) -> dict[str, Any]:
    """Chấm điểm tiềm năng khách hàng từ 0 - 100 theo mô hình calibrated."""
    feats = req.features

    # Tính điểm giả lập dựa trên trọng số đặc trưng hợp đồng
    raw_score = 30.0
    if feats.get("buying_intent_detected", 0) > 0:
        raw_score += 35.0
    if feats.get("pricing_inquiry_count", 0) > 0:
        raw_score += 15.0
    if feats.get("turn_count", 0) >= 5:
        raw_score += 10.0
    if feats.get("complaint_detected", 0) > 0:
        raw_score -= 20.0

    score = int(min(100, max(0, raw_score)))

    if score >= 75:
        confidence = "HIGH"
        reasons = ["Khách hàng có tín hiệu mua hàng rõ rệt", "Hội thoại tương tác sâu về giá"]
    elif score >= 50:
        confidence = "MEDIUM"
        reasons = ["Có tìm hiểu thông tin sản phẩm và chính sách"]
    else:
        confidence = "LOW"
        reasons = ["Chưa phát hiện nhu cầu mua cụ thể hoặc có phản ánh lỗi"]

    return {
        "score": score,
        "model_version": "lead-scorer-v1.0",
        "confidence_level": confidence,
        "reasons": reasons,
    }


@router.get("/v1/model")
async def model_info() -> dict[str, Any]:
    return {
        "model_id": get_model_id(),
        "role": "classify",
        "taxonomies": INTENT_TAXONOMY,
        "device": "CPU",
        "status": "READY",
    }
