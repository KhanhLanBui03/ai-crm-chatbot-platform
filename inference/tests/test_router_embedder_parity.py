"""Parity: embedder port trong ai-inference phải ra ĐÚNG vector như lúc huấn luyện.

So ``inference/src/roles/router_embedder.py`` (đọc JSON) với ``SemanticDenseEmbedder``
gốc trong ``artifacts/router_branch_c.joblib`` trên 200 câu test người thật. Lệch là router
nhận vector khác lúc huấn luyện mà không có lỗi nào báo ra — đúng loại lỗi từng xảy ra khi
container âm thầm bỏ qua mô hình.

Test cần ``joblib`` + scikit-learn (để mở pickle) — chạy ở máy dev / CI, không chạy trong image.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
EMB_JSON = REPO / "artifacts" / "router_embedder.json"
JOBLIB = REPO / "artifacts" / "router_branch_c.joblib"
ONNX = REPO / "artifacts" / "router_model.onnx"
TEST_SET = REPO / "data" / "intent_test_human.jsonl"

joblib = pytest.importorskip("joblib")
ort = pytest.importorskip("onnxruntime")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ported():
    mod = _load("router_embedder_under_test", REPO / "inference" / "src" / "roles" / "router_embedder.py")
    return mod.RouterEmbedder.from_json(EMB_JSON)


@pytest.fixture(scope="module")
def original():
    sys.path.insert(0, str(REPO / "ai-service" / "src"))
    return joblib.load(JOBLIB)


@pytest.fixture(scope="module")
def texts():
    return [json.loads(line)["text"] for line in TEST_SET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_json_khop_hash_trong_so():
    digest = hashlib.sha256(EMB_JSON.read_bytes()).hexdigest()
    assert f"{digest}  artifacts/router_embedder.json" in (REPO / "artifacts" / "DATA_HASHES.txt").read_text(
        encoding="utf-8"
    )


def test_vector_khop_embedder_goc(ported, original, texts):
    orig = original["embedder"]
    assert ported.dim == orig.dim and ported.n_docs == orig.n_docs
    max_diff = max(float(np.max(np.abs(ported.transform_single(t) - orig.transform_single(t)))) for t in texts)
    assert max_diff < 1e-6, max_diff


def test_nhan_onnx_khop_200_cau(ported, original, texts):
    sess = ort.InferenceSession(str(ONNX), providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name

    def labels(emb):
        return [str(sess.run(None, {name: emb.transform_single(t).reshape(1, -1).astype(np.float32)})[0][0])
                for t in texts]

    assert labels(ported) == labels(original["embedder"])
    assert len(texts) == 200


def test_thu_tu_lop_khop_logreg(ported, original):
    assert ported.classes == [str(c) for c in original["classifier_lr"].classes_]


def _fresh_classify(monkeypatch):
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    monkeypatch.delenv("EXPECTED_MODEL_ID", raising=False)
    return _load("classify_under_test", REPO / "inference" / "src" / "roles" / "classify.py")


def test_classify_nap_duoc_mo_hinh_khong_can_joblib(monkeypatch):
    mod = _fresh_classify(monkeypatch)
    ok, msg = mod.check_invariants()
    assert ok, msg
    assert mod._EMBEDDER is not None and mod._ONNX_SESSION is not None


def test_thieu_artifact_thi_ready_fail_closed(monkeypatch):
    mod = _fresh_classify(monkeypatch)
    monkeypatch.setattr(mod, "_find_path", lambda _rel: None)
    ok, msg = mod.check_invariants()
    assert not ok and "ROUTER CHƯA SẴN SÀNG" in msg
