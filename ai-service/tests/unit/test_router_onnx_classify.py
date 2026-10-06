"""Kiểm thử tự động cho Router ONNX INT8 và kiến trúc định tuyến 3 tầng (UC022 3/4).

Đặc tả kiểm thử theo Master Plan §5.9:
1. Xác thực tệp ONNX INT8 tồn tại và khớp mã băm SHA-256 đóng băng.
2. Kiểm tra Cổng Parity (sai số xác suất giữa Sklearn và ONNX < 1e-4).
3. Đo đạc độ trễ suy luận trên CPU (p95 < 5 ms, vượt xa ngân sách 60 ms).
4. Kiểm tra đầy đủ 3 tầng: Rule Regex -> ONNX Model -> Abstention Gate Fallback sang LLM.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

# Đảm bảo ai-service/src và inference nằm trên sys.path
_current_dir = Path(__file__).resolve().parent
_repo_root = _current_dir.parent.parent.parent
_ai_service_src = (_repo_root / "ai-service" / "src").resolve()
_inference_dir = (_repo_root / "inference").resolve()

if str(_ai_service_src) not in sys.path:
    sys.path.insert(0, str(_ai_service_src))
if str(_inference_dir) not in sys.path:
    sys.path.insert(0, str(_inference_dir))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# venv ai-service cố ý KHÔNG có onnxruntime (luật 5, cổng chặn CI) — test này chỉ chạy ở venv
# có tầng suy luận; ở ai-service thì bỏ qua cả module thay vì làm hỏng lượt thu thập test.
ort = pytest.importorskip("onnxruntime")

INTENT_TAXONOMY = [
    "GREETING",
    "KB_SEARCH",
    "PRICING_POLICY",
    "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN",
    "TECH_ERROR",
    "BUYING_INTENT",
]


def _compute_sha256(filepath: str | Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_onnx_model_file_exists_and_hash():
    """Kiểm tra tệp ONNX INT8 tồn tại và khớp mã băm trong DATA_HASHES.txt."""
    onnx_path = _repo_root / "artifacts" / "router_model.onnx"
    assert onnx_path.is_file(), f"Không tìm thấy tệp {onnx_path}"

    onnx_hash = _compute_sha256(onnx_path)
    assert len(onnx_hash) == 64

    # Kiểm tra kích thước mô hình siêu nhẹ (< 100 KB)
    file_size_kb = onnx_path.stat().st_size / 1024
    assert file_size_kb < 100.0, f"Mô hình ONNX quá nặng: {file_size_kb:.2f} KB"

    # Kiểm tra mã băm ghi nhận trong DATA_HASHES.txt
    hashes_file = _repo_root / "artifacts" / "DATA_HASHES.txt"
    assert hashes_file.is_file()
    hashes_content = hashes_file.read_text(encoding="utf-8")
    assert onnx_hash in hashes_content, "Mã băm ONNX chưa được ghi nhận vào DATA_HASHES.txt"


def test_onnx_session_inference_parity():
    """Kiểm tra Cổng Parity: Sai số giữa Sklearn gốc và ONNX INT8 phải < 1e-4."""
    onnx_path = _repo_root / "artifacts" / "router_model.onnx"
    joblib_path = _repo_root / "artifacts" / "router_branch_c.joblib"
    assert onnx_path.is_file() and joblib_path.is_file()

    # Nạp mô hình gốc Sklearn
    artifact = joblib.load(joblib_path)
    clf_lr = artifact["classifier_lr"]
    embedder = artifact["embedder"]

    # Khởi tạo ONNX session
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name

    # Lấy mẫu thử nghiệm từ intent_test_human.jsonl
    test_file = _repo_root / "data" / "intent_test_human.jsonl"
    assert test_file.is_file()
    sample_texts = []
    with open(test_file, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 50:
                break
            sample_texts.append(json.loads(line)["text"])

    # Vector hóa
    X_samples = embedder.transform(sample_texts).astype(np.float32)

    # Dự đoán bằng Sklearn
    probs_sk = clf_lr.predict_proba(X_samples)

    # Dự đoán bằng ONNX
    res_onnx = sess.run(None, {input_name: X_samples})
    probs_onnx = np.array([[row[c] for c in clf_lr.classes_] for row in res_onnx[1]])

    # Kiểm tra sai số tuyệt đối lớn nhất
    max_diff = float(np.max(np.abs(probs_sk - probs_onnx)))
    assert max_diff < 1e-4, f"Cổng Parity thất bại: sai số {max_diff:.2e} >= 1e-4"


def test_onnx_cpu_latency_under_5ms():
    """Kiểm tra độ trễ suy luận trên CPU: p95 phải < 5 ms (ngân sách Master Plan <= 60 ms)."""
    onnx_path = _repo_root / "artifacts" / "router_model.onnx"
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name

    # Sinh vector 1024 chiều ngẫu nhiên giả lập embedding
    dummy_vec = np.random.randn(1, 1024).astype(np.float32)
    norm = np.linalg.norm(dummy_vec)
    dummy_vec = dummy_vec / norm

    # Warmup
    for _ in range(10):
        sess.run(None, {input_name: dummy_vec})

    # Đo 100 lần
    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        sess.run(None, {input_name: dummy_vec})
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    p95_lat = float(np.percentile(latencies, 95))
    p50_lat = float(np.percentile(latencies, 50))

    assert p95_lat < 5.0, f"Độ trễ p95 ({p95_lat:.3f} ms) vượt ngưỡng 5 ms"
    assert p50_lat < 2.0, f"Độ trễ p50 ({p50_lat:.3f} ms) vượt ngưỡng 2 ms"


def test_classify_endpoint_3_tiers(monkeypatch):
    """Kiểm thử tích hợp endpoint /v1/classify với kiến trúc định tuyến 3 tầng."""
    monkeypatch.setenv("MODEL_ROLE", "classify")
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    monkeypatch.delenv("EXPECTED_MODEL_ID", raising=False)

    # Nạp module classify từ inference
    classify_file = _inference_dir / "src" / "roles" / "classify.py"
    spec = importlib.util.spec_from_file_location("classify_role_mod_test", str(classify_file))
    classify_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(classify_mod)

    app = FastAPI()
    app.include_router(classify_mod.router)
    client = TestClient(app)

    # 1. TẦNG 1 (Rule-based Regex): Câu hỏi khẩn cấp chuyển người thật
    req_t1 = {"text": "Cho mình gặp nhân viên tư vấn người thật trực tiếp"}
    res_tier1 = client.post("/v1/classify", json=req_t1)
    assert res_tier1.status_code == 200
    data_t1 = res_tier1.json()
    assert data_t1["intent"] == "HANDOFF_HUMAN"
    assert data_t1["tier_used"] == "tier1_rule"
    assert data_t1["fallback_to_llm"] is False
    assert data_t1["confidence"] >= 0.95

    # 2. TẦNG 2 (ONNX Model INT8): Câu hỏi báo giá có confidence vượt ngưỡng
    monkeypatch.setenv("ROUTER_ABSTENTION_THRESHOLD", "0.40")
    req_t2 = {"text": "Cho mình hỏi giá gói Pro bao nhiêu một tháng?"}
    res_tier2 = client.post("/v1/classify", json=req_t2)
    assert res_tier2.status_code == 200
    data_t2 = res_tier2.json()
    assert data_t2["intent"] == "PRICING_POLICY"
    assert data_t2["tier_used"] == "tier2_onnx"
    assert data_t2["fallback_to_llm"] is False
    assert data_t2["confidence"] > 0.40
    assert len(data_t2["probabilities"]) == len(INTENT_TAXONOMY)

    # 3. TẦNG 3 (Abstention Gate): Ngưỡng yêu cầu cao khiến câu hỏi kích hoạt Fallback LLM
    monkeypatch.setenv("ROUTER_ABSTENTION_THRESHOLD", "0.90")
    req_t3 = {"text": "Cho mình hỏi giá gói Pro bao nhiêu một tháng?"}
    res_tier3 = client.post("/v1/classify", json=req_t3)
    assert res_tier3.status_code == 200
    data_t3 = res_tier3.json()
    assert data_t3["tier_used"] == "tier3_llm_fallback"
    assert data_t3["fallback_to_llm"] is True
