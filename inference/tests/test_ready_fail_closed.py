import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Thêm thư mục inference vào sys.path để import src
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_embed_ready_normal(monkeypatch):
    monkeypatch.setenv("MODEL_ROLE", "embed")
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    monkeypatch.delenv("EXPECTED_MODEL_ID", raising=False)
    monkeypatch.delenv("FORCE_READY_FAIL", raising=False)

    from src.entrypoint import create_app
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


def test_embed_ready_fail_closed_on_model_mismatch(monkeypatch):
    """FAIL-CLOSED: Khi model_id không khớp EXPECTED_MODEL_ID, /ready BẮT BUỘC trả 503."""
    monkeypatch.setenv("MODEL_ROLE", "embed")
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    monkeypatch.setenv("MODEL_ID", "BAAI/bge-m3")
    monkeypatch.setenv("EXPECTED_MODEL_ID", "wrong/mismatched-model-768")

    from src.entrypoint import create_app
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

    from src.entrypoint import create_app
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
