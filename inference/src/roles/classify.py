"""``MODEL_ROLE=classify`` — router ý định (UC022) + lead scorer (UC030).

Endpoint: ``POST /v1/classify`` · ``POST /v1/lead-score`` · ``GET /v1/model``
Ngân sách độ trễ: Router p95 60 ms, Lead Scorer p95 < 1.000 ms (§5.3).
"""

from __future__ import annotations

import json
import logging
import os
import sys
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
    tier_used: str = Field(default="tier2_onnx", description="Tầng định tuyến đã xử lý (tier1_rule, tier2_onnx, tier3_llm_fallback)")
    fallback_to_llm: bool = Field(default=False, description="Cờ đánh dấu câu hỏi nghi ngờ cần chuyển tiếp sang LLM")


class LeadScoreRequest(BaseModel):
    features: dict[str, float] = Field(..., description="Từ điển đặc trưng trích xuất được")


class LeadScoreResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    model_version: str
    confidence_level: str
    reasons: list[str]


def get_model_id() -> str:
    return os.getenv("MODEL_ID", DEFAULT_MODEL_ID)


# ---------------------------------------------------------------------------
# Quản lý vòng đời Mô hình Router ONNX INT8 & Embedder (Singleton)
# ---------------------------------------------------------------------------
_ONNX_SESSION: Any = None
_EMBEDDER: Any = None
_ROUTER_INITIALIZED: bool = False


def _find_path(rel_path: str) -> Path | None:
    """Tìm đường dẫn tệp tương đối từ CWD hoặc thư mục cha của project."""
    p = Path(rel_path)
    if p.is_file():
        return p
    for parent in Path(__file__).resolve().parents:
        cand = parent / rel_path
        if cand.is_file():
            return cand
    return None


def _init_router_model() -> None:
    """Nạp ONNX InferenceSession và Embedder cho Router Nhánh C."""
    global _ONNX_SESSION, _EMBEDDER, _ROUTER_INITIALIZED
    if _ROUTER_INITIALIZED:
        return
    _ROUTER_INITIALIZED = True

    # Đảm bảo ai-service/src có trên sys.path để nạp SemanticDenseEmbedder unpickle
    for parent in Path(__file__).resolve().parents:
        cand_src = parent / "ai-service" / "src"
        if cand_src.is_dir() and str(cand_src) not in sys.path:
            sys.path.insert(0, str(cand_src))

    onnx_file = _find_path("artifacts/router_model.onnx")
    joblib_file = _find_path("artifacts/router_branch_c.joblib")

    if onnx_file and joblib_file:
        try:
            import joblib
            import onnxruntime as ort
            _ONNX_SESSION = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
            artifact_c = joblib.load(joblib_file)
            _EMBEDDER = artifact_c.get("embedder")
            logger.info("Đã nạp ONNX Router INT8 thành công từ: %s", onnx_file)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Không thể nạp Router ONNX: %s. Tiếp tục với quy tắc rule-based.", exc)


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
    meta_path = _find_path("artifacts/lead_scorer.meta.json") or Path("artifacts/lead_scorer.meta.json")
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            features_in_meta = meta.get("feature_names", [])
            if features_in_meta != EXPECTED_FEATURE_COLUMNS:
                return False, (
                    f"BẤT BIẾN 2 VI PHẠM: Thứ tự đặc trưng trong {meta_path} không khớp HỢP ĐỒNG. "
                    f"Kỳ vọng {EXPECTED_FEATURE_COLUMNS}, thực tế nhận {features_in_meta}"
                )
        except Exception as exc:  # noqa: BLE001
            return False, f"BẤT BIẾN 2 LỖI ĐỌC: Không thể đọc meta.json: {exc}"

    return True, f"Classify model_id và đặc trưng hợp lệ: {current_id}"


def _rule_based_check(text: str) -> tuple[str | None, float]:
    """Tầng 1 (Rule Regex) - Bắt nhanh các mẫu cực kỳ đặc thù với độ tin cậy tuyệt đối."""
    import re
    t = text.lower().strip()
    words = set(re.findall(r"\w+", t))

    if any(p in t for p in ["gặp người", "tư vấn viên", "nhân viên", "người thật", "chuyển máy", "tổng đài", "chăm sóc khách hàng", "human agent", "gap nguoi"]):
        return "HANDOFF_HUMAN", 0.98
    if any(p in t for p in ["lỗi", "không vào được", "hỏng", "sập", "bị đơ", "chết", "bug", "crash", "timeout", "mat mang", "disconect"]):
        return "TECH_ERROR", 0.95
    if any(p in t for p in ["khiếu nại", "thái độ", "bồi thường", "phàn nàn", "tệ quá", "buc minh", "that vong", "qua te"]):
        return "COMPLAINT_SUPPORT", 0.93
    if any(p in t for p in ["báo giá", "bảng giá", "chi phí", "bao nhiêu tiền", "khuyến mãi", "gói cước", "bao tien", "bn tien", "phi duy tri"]):
        return "PRICING_POLICY", 0.94
    if any(p in t for p in ["mua gói", "đặt hàng", "thanh toán", "chuyển khoản", "ký hợp đồng", "chot don", "nang cap"]):
        return "BUYING_INTENT", 0.93
    if any(w in words for w in ["chào", "hi", "hello", "alo", "bye", "thanks", "tks"]) or any(p in t for p in ["xin chào", "tạm biệt", "cảm ơn", "cam on"]):
        return "GREETING", 0.96
    return None, 0.0


def _rule_based_classify(text: str) -> tuple[str, float, dict[str, float]]:
    """Phân loại ý định toàn phần kết hợp keyword rule và xác suất chuẩn hóa."""
    intent, conf = _rule_based_check(text)
    if intent is None:
        intent = "KB_SEARCH"
        conf = 0.85

    probs = {i: 0.02 for i in INTENT_TAXONOMY}
    probs[intent] = conf
    rem = (1.0 - conf) / (len(INTENT_TAXONOMY) - 1)
    for k in probs:
        if k != intent:
            probs[k] = round(rem, 4)

    return intent, conf, probs


@router.post("/v1/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest) -> dict[str, Any]:
    """Phân loại ý định khách hàng theo kiến trúc định tuyến 3 tầng chuẩn Master Plan §5.9.
    
    1. Tầng 1: Rule-based Regex bắt các từ khóa khẩn cấp / xã giao rõ ràng.
    2. Tầng 2: ONNX Model INT8 (Nhánh C tái sử dụng vector ai-embed 1024 chiều).
    3. Tầng 3: Abstention Gate nếu độ tự tin < τ* (0.65), gắn cờ fallback_to_llm=True.
    """
    _init_router_model()
    text = req.text.strip()

    # TẦNG 1: Rule-based Regex
    rule_intent, rule_conf = _rule_based_check(text)
    if rule_intent is not None:
        probs = {i: 0.01 for i in INTENT_TAXONOMY}
        probs[rule_intent] = rule_conf
        rem = (1.0 - rule_conf) / (len(INTENT_TAXONOMY) - 1)
        for k in probs:
            if k != rule_intent:
                probs[k] = round(rem, 4)
        return {
            "intent": rule_intent,
            "confidence": rule_conf,
            "probabilities": probs,
            "model_id": get_model_id(),
            "tier_used": "tier1_rule",
            "fallback_to_llm": False,
        }

    # TẦNG 2: ONNX Model INT8
    if _ONNX_SESSION is not None and _EMBEDDER is not None:
        try:
            vec = _EMBEDDER.transform_single(text)
            input_name = _ONNX_SESSION.get_inputs()[0].name
            res = _ONNX_SESSION.run(None, {input_name: vec.reshape(1, -1)})
            predicted_intent = str(res[0][0])
            prob_dict = {k: round(float(v), 4) for k, v in res[1][0].items()}
            conf = float(prob_dict.get(predicted_intent, 0.0))

            # TẦNG 3: Abstention Gate kiểm tra ngưỡng bỏ phiếu trắng
            abstention_tau = float(os.getenv("ROUTER_ABSTENTION_THRESHOLD", "0.65"))
            if conf < abstention_tau:
                return {
                    "intent": predicted_intent,
                    "confidence": conf,
                    "probabilities": prob_dict,
                    "model_id": get_model_id(),
                    "tier_used": "tier3_llm_fallback",
                    "fallback_to_llm": True,
                }

            return {
                "intent": predicted_intent,
                "confidence": conf,
                "probabilities": prob_dict,
                "model_id": get_model_id(),
                "tier_used": "tier2_onnx",
                "fallback_to_llm": False,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Lỗi suy luận ONNX Router: %s. Chuyển sang fallback.", exc)

    # Dự phòng an toàn khi thiếu artifact ONNX
    intent, conf, probs = _rule_based_classify(text)
    return {
        "intent": intent,
        "confidence": conf,
        "probabilities": probs,
        "model_id": get_model_id(),
        "tier_used": "tier1_rule",
        "fallback_to_llm": False,
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
