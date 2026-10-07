import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Thêm thư mục inference vào đầu sys.path và cô lập namespace src
_inference_dir = str(Path(__file__).resolve().parent.parent)
if sys.path[0] != _inference_dir:
    sys.path.insert(0, _inference_dir)

if "src" in sys.modules and ("src" not in getattr(sys.modules["src"], "__file__", "") or _inference_dir not in str(getattr(sys.modules["src"], "__file__", ""))):
    for mod_name in list(sys.modules.keys()):
        if mod_name == "src" or mod_name.startswith("src."):
            del sys.modules[mod_name]


def _get_create_app():
    _inference_dir = str(Path(__file__).resolve().parent.parent)
    if sys.path[0] != _inference_dir:
        sys.path.insert(0, _inference_dir)
    if "src" in sys.modules and ("src" not in getattr(sys.modules["src"], "__file__", "") or _inference_dir not in str(getattr(sys.modules["src"], "__file__", ""))):
        for mod_name in list(sys.modules.keys()):
            if mod_name == "src" or mod_name.startswith("src."):
                del sys.modules[mod_name]
    from src.entrypoint import create_app
    return create_app


_MODELS = Path(__file__).resolve().parents[2] / "artifacts" / "models"
_CO_MODEL_NHUNG = (_MODELS / "bge-m3-int8.onnx").is_file() and (_MODELS / "tokenizer.json").is_file()


@pytest.mark.skipif(not _CO_MODEL_NHUNG, reason="thiếu artifacts/models/bge-m3-int8.onnx + tokenizer.json")
def test_embed_ready_normal(monkeypatch):
    monkeypatch.setenv("MODEL_ROLE", "embed")
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    monkeypatch.delenv("EXPECTED_MODEL_ID", raising=False)
    monkeypatch.delenv("FORCE_READY_FAIL", raising=False)

    create_app = _get_create_app()
    app = create_app()
    client = TestClient(app)

    # 1. Health probe trả 200
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "UP"

    # 2. Ready probe trả 200 khi bất biến thỏa mãn
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    data = res_ready.json()
    assert data["ready"] is True
    assert data["role"] == "embed"

    # 3. Test /v1/embed
    res_embed = client.post("/v1/embed", json={"text": "Xin chào thế giới"})
    assert res_embed.status_code == 200
    embed_data = res_embed.json()
    assert len(embed_data["embedding"]) == 1024
    assert embed_data["dim"] == 1024
    assert embed_data["model_version"].startswith("int8-")


def test_embed_ready_fail_closed_khi_thieu_model(monkeypatch, tmp_path):
    """FAIL-CLOSED: không nạp được model nhúng thì /ready 503 và /v1/embed 503 — không trả vector giả."""
    monkeypatch.setenv("MODEL_ROLE", "embed")
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    monkeypatch.delenv("EXPECTED_MODEL_ID", raising=False)
    monkeypatch.setenv("EMBED_MODEL_PATH", str(tmp_path / "khong-co.onnx"))

    client = TestClient(_get_create_app()())

    assert client.get("/health").status_code == 200
    res_ready = client.get("/ready")
    assert res_ready.status_code == 503
    assert any("CHƯA NẠP ĐƯỢC MODEL NHÚNG" in v for v in res_ready.json()["violations"])
    assert client.post("/v1/embed", json={"text": "xin chào"}).status_code == 503
    assert client.get("/v1/model").json()["status"] == "NOT_READY"


def test_embed_ready_fail_closed_on_model_mismatch(monkeypatch):
    """FAIL-CLOSED: Khi model_id không khớp EXPECTED_MODEL_ID, /ready BẮT BUỘC trả 503."""
    monkeypatch.setenv("MODEL_ROLE", "embed")
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    monkeypatch.setenv("MODEL_ID", "BAAI/bge-m3")
    monkeypatch.setenv("EXPECTED_MODEL_ID", "wrong/mismatched-model-768")

    create_app = _get_create_app()
    app = create_app()
    client = TestClient(app)

    # Liveness probe vẫn trả 200 (container còn sống)
    res_health = client.get("/health")
    assert res_health.status_code == 200

    # Nhưng Readiness probe PHẢI trả 503 Service Unavailable để Kubernetes/Gateway không định tuyến traffic vào
    res_ready = client.get("/ready")
    assert res_ready.status_code == 503
    data = res_ready.json()
    assert data["ready"] is False
    assert data["code"] == "INVARIANT_VIOLATION"
    assert any("BẤT BIẾN 1 VI PHẠM" in v for v in data["violations"])


def test_classify_ready_and_endpoints(monkeypatch):
    monkeypatch.setenv("MODEL_ROLE", "classify")
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    monkeypatch.delenv("EXPECTED_MODEL_ID", raising=False)

    create_app = _get_create_app()
    app = create_app()
    client = TestClient(app)

    # 1. Ready probe trả 200
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200

    # 2. Classify intent
    res_cls = client.post("/v1/classify", json={"text": "Cho mình hỏi giá gói Pro bao nhiêu một tháng?"})
    assert res_cls.status_code == 200
    assert res_cls.json()["intent"] == "PRICING_POLICY"

    # 3. Lead score
    res_score = client.post(
        "/v1/lead-score",
        json={"features": {"buying_intent_detected": 1.0, "pricing_inquiry_count": 2.0, "turn_count": 6.0}}
    )
    assert res_score.status_code == 200
    assert res_score.json()["score"] >= 75
    assert res_score.json()["confidence_level"] == "HIGH"
