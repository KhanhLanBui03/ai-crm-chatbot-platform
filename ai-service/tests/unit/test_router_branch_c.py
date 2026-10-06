"""Kiểm thử tự động cho Bộ định tuyến Ý định Nhánh C (UC022 2/4).

Đảm bảo:
1. Artifact model tồn tại, toàn vẹn mã băm SHA-256 trong DATA_HASHES.txt (§5.8).
2. Tương thích 100% với taxonomy 7 nhánh ý định theo hợp đồng Master Plan §5.9.
3. Độ trễ router thêm (overhead) < 5 ms trên CPU.
4. Chất lượng phân loại trên tập test người thật đạt chỉ tiêu kỹ thuật.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

# Đảm bảo ai-service/src nằm trên sys.path để nạp đúng module ai.inference.embedder
_src_dir = (Path(__file__).resolve().parent.parent.parent / "src").resolve()
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
import joblib  # noqa: E402
import numpy as np  # noqa: E402

# Đường dẫn neo vào gốc repo, không vào thư mục đang đứng: CI và lệnh `pytest tests` chạy từ
# ai-service/, nên Path("artifacts/…") tương đối sẽ trỏ nhầm sang ai-service/artifacts/.
_REPO = Path(__file__).resolve().parents[3]

TAXONOMY_7 = [
    "GREETING",
    "KB_SEARCH",
    "PRICING_POLICY",
    "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN",
    "TECH_ERROR",
    "BUYING_INTENT",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_branch_c_artifact_integrity():
    """Kiểm tra artifact model Nhánh C tồn tại và khớp mã băm trong DATA_HASHES.txt."""
    artifact_path = _REPO / "artifacts/router_branch_c.joblib"
    assert artifact_path.is_file(), f"Không tìm thấy model artifact {artifact_path}"

    current_hash = _sha256(artifact_path)
    hashes_file = _REPO / "artifacts/DATA_HASHES.txt"
    assert hashes_file.is_file(), "Không tìm thấy artifacts/DATA_HASHES.txt"

    hashes_content = hashes_file.read_text(encoding="utf-8")
    assert current_hash in hashes_content, (
        f"Mã hash {current_hash} của {artifact_path} không tồn tại trong DATA_HASHES.txt"
    )


def test_branch_c_model_contract_and_prediction():
    """Kiểm tra hợp đồng đầu ra của Nhánh C: Đủ 7 nhãn và sinh vector chuẩn 1024 chiều."""
    artifact = joblib.load(_REPO / "artifacts/router_branch_c.joblib")
    assert artifact.get("branch") == "branch_c"
    assert artifact.get("taxonomy") == TAXONOMY_7

    embedder = artifact["embedder"]
    clf = artifact["classifier_knn"]

    sample_text = "Em muốn hỏi giá gói CRM Pro cho 10 nhân viên là bao nhiêu ạ?"
    vec = embedder.transform([sample_text])
    assert vec.shape == (1, 1024), f"Kỳ vọng vector 1024 chiều, thực tế {vec.shape}"

    pred_intent = clf.predict(vec)[0]
    assert pred_intent in TAXONOMY_7, (
        f"Nhãn dự đoán {pred_intent} không nằm trong taxonomy chuẩn"
    )
    assert pred_intent == "PRICING_POLICY", (
        f"Câu hỏi về giá phải đoán là PRICING_POLICY, nhận: {pred_intent}"
    )


def test_branch_c_latency_overhead_budget():
    """Kiểm tra ngân sách độ trễ router thêm (Overhead): p95 < 5 ms trên CPU (§5.3)."""
    artifact = joblib.load(_REPO / "artifacts/router_branch_c.joblib")
    clf = artifact["classifier_lr"]

    dummy_vec = np.random.randn(1, 1024).astype(np.float32)
    dummy_vec /= np.linalg.norm(dummy_vec)

    latencies_ms = []
    # Đo 100 lần suy luận
    for _ in range(100):
        t0 = time.perf_counter()
        _ = clf.predict_proba(dummy_vec)
        latencies_ms.append((time.perf_counter() - t0) * 1000)

    p95_ms = float(np.percentile(latencies_ms, 95))
    assert p95_ms < 5.0, f"Độ trễ router overhead ({p95_ms:.3f} ms) vượt ngân sách 5 ms"


def test_branch_c_evaluation_report_metrics():
    """Kiểm tra báo cáo đánh giá router_branch_c_eval.json có đủ các chỉ số khoa học."""
    report_file = _REPO / "docs/report/router_branch_c_eval.json"
    assert report_file.is_file(), f"Không tìm thấy báo cáo {report_file}"

    with open(report_file, encoding="utf-8") as f:
        data = json.load(f)

    perf = data.get("performance", {})
    assert "knn" in perf
    assert "hybrid_router" in perf
    assert perf["knn"]["accuracy"] >= 0.70
    assert perf["knn"]["macro_f1"] >= 0.70

    per_class = data.get("per_class_metrics", {})
    for intent in TAXONOMY_7:
        assert intent in per_class, f"Thiếu metric cho intent {intent}"
        assert per_class[intent]["f1_score"] >= 0.60, (
            f"F1-score của intent {intent} ({per_class[intent]['f1_score']}) dưới 0.60"
        )
