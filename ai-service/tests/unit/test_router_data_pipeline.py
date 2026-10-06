"""Kiểm thử tính toàn vẹn của tập dữ liệu huấn luyện UC022 và chỉ số Cohen's Kappa."""

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

# Đường dẫn neo vào gốc repo, không vào thư mục đang đứng: CI và lệnh `pytest tests` chạy từ
# ai-service/, nên Path("artifacts/…") tương đối sẽ trỏ nhầm sang ai-service/artifacts/.
_REPO = Path(__file__).resolve().parents[3]


def test_intent_train_raw_distribution():
    """Kiểm tra tập train thô có đúng 3.000 mẫu và chuẩn phân bổ 6 văn phong."""
    raw_path = _REPO / "data/intent_train_raw.jsonl"
    assert raw_path.exists(), "Không tìm thấy data/intent_train_raw.jsonl"

    records = []
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # 1. Đúng 3.000 mẫu
    assert len(records) == 3000, f"Kỳ vọng 3.000 mẫu raw, thực tế nhận {len(records)}"

    # 2. Kiểm tra phân bổ 6 văn phong
    style_counts = Counter(r["style"] for r in records)
    assert style_counts["polite_full"] == 750, "Sai số lượng polite_full (kỳ vọng 750 = 25%)"
    assert style_counts["short_abbrev"] == 750, "Sai số lượng short_abbrev (kỳ vọng 750 = 25%)"
    assert style_counts["no_accent"] == 600, "Sai số lượng no_accent (kỳ vọng 600 = 20%)"
    assert style_counts["typo"] == 450, "Sai số lượng typo (kỳ vọng 450 = 15%)"
    assert style_counts["en_mix"] == 300, "Sai số lượng en_mix (kỳ vọng 300 = 10%)"
    assert style_counts["emoji"] == 150, "Sai số lượng emoji (kỳ vọng 150 = 5%)"


def test_intent_train_dedup_integrity():
    """Kiểm tra tập train sau khử trùng lặp và mã băm đóng băng SHA-256."""
    dedup_path = _REPO / "data/intent_train_dedup.jsonl"
    assert dedup_path.exists(), "Không tìm thấy data/intent_train_dedup.jsonl"

    records = []
    with open(dedup_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Tỉ lệ loại bỏ phản ánh số bản sao mà build_router_data_and_eval.py CHỦ ĐỘNG chèn để đủ
    # 3.000 mẫu thô — đây là kiểm tra hồi quy của pipeline, không phải số đo dữ liệu tự nhiên.
    raw_count = 3000
    clean_count = len(records)
    removed_count = raw_count - clean_count
    dedup_rate = (removed_count / raw_count) * 100

    assert 20.0 <= dedup_rate <= 40.0, f"Tỉ lệ khử trùng lặp bất thường: {dedup_rate:.2f}%"

    # Xác thực mã hash trong artifacts/DATA_HASHES.txt
    file_hash = hashlib.sha256(dedup_path.read_bytes()).hexdigest()
    hashes_path = _REPO / "artifacts/DATA_HASHES.txt"
    assert hashes_path.exists()
    assert f"data/intent_train_dedup.jsonl:{file_hash}" in hashes_path.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# COHEN'S KAPPA — scripts/compute_annotation_kappa.py đọc nhãn THẬT của hai người.
# Không kiểm "kappa >= 0,85" hay "đúng 13 ca bất đồng": đó là kết quả, không phải hành vi —
# và bản cũ đạt được hai điều đó chỉ vì nhãn Dev A bị dựng từ nhãn vàng.
# ══════════════════════════════════════════════════════════════════════════════

_spec = importlib.util.spec_from_file_location(
    "kappa", _REPO / "scripts/compute_annotation_kappa.py"
)
kappa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kappa)

_ITEMS = [
    {"id": 1, "text": "chào shop", "intent": "GREETING"},
    {"id": 2, "text": "giá gói pro", "intent": "PRICING_POLICY"},
    {"id": 3, "text": "app bị crash", "intent": "TECH_ERROR"},
    {"id": 4, "text": "cho gặp người thật", "intent": "HANDOFF_HUMAN"},
]


def test_kappa_khop_cong_thuc():
    # Ví dụ tính tay: p_o = 3/4; mỗi người 2 nhãn A/B -> p_e = 0,5; kappa = 0,5
    r = kappa.cohens_kappa(["GREETING", "GREETING", "KB_SEARCH", "KB_SEARCH"],
                           ["GREETING", "KB_SEARCH", "KB_SEARCH", "KB_SEARCH"])
    assert r["p_o"] == 0.75
    assert abs(r["p_e"] - 0.5) < 1e-12
    assert abs(r["kappa"] - 0.5) < 1e-12


def test_kappa_khop_sklearn():
    from sklearn.metrics import cohen_kappa_score

    a = ["GREETING", "KB_SEARCH", "TECH_ERROR", "TECH_ERROR", "BUYING_INTENT", "KB_SEARCH"]
    b = ["GREETING", "KB_SEARCH", "COMPLAINT_SUPPORT", "TECH_ERROR", "PRICING_POLICY", "KB_SEARCH"]
    assert abs(kappa.cohens_kappa(a, b)["kappa"] - cohen_kappa_score(a, b)) < 1e-12


def _write_csv(path: Path, labels: dict[int, str]) -> None:
    lines = ["id,text,intent"] + [f"{i},câu {i},{lab}" for i, lab in labels.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def test_bao_cao_tu_hai_phieu_rieng(tmp_path: Path):
    _write_csv(tmp_path / "a.csv",
               {1: "GREETING", 2: "PRICING_POLICY", 3: "TECH_ERROR", 4: "HANDOFF_HUMAN"})
    _write_csv(tmp_path / "b.csv",
               {1: "GREETING", 2: "BUYING_INTENT", 3: "TECH_ERROR", 4: "HANDOFF_HUMAN"})
    rep = kappa.build_report(
        _ITEMS,
        kappa.load_annotations(tmp_path / "a.csv"),
        kappa.load_annotations(tmp_path / "b.csv"),
        sources={},
    )
    assert rep["sample_count"] == 4 and rep["disagreed_count"] == 1
    assert rep["disagreements"][0] == {
        "id": 2, "text": "giá gói pro", "dev_a": "PRICING_POLICY",
        "dev_b": "BUYING_INTENT", "current_gold": "PRICING_POLICY",
    }


@pytest.mark.parametrize("labels, msg", [
    ({1: "GREETING", 2: ""}, "chưa điền"),
    ({1: "GREETING", 2: "PRICING"}, "không thuộc"),
])
def test_phieu_sai_bi_tu_choi(tmp_path: Path, labels: dict[int, str], msg: str):
    _write_csv(tmp_path / "x.csv", labels)
    with pytest.raises(kappa.AnnotationError, match=msg):
        kappa.load_annotations(tmp_path / "x.csv")


def test_phieu_thieu_cau_bi_tu_choi(tmp_path: Path):
    _write_csv(tmp_path / "a.csv", {1: "GREETING", 2: "PRICING_POLICY", 3: "TECH_ERROR"})
    full = {1: "GREETING", 2: "PRICING_POLICY", 3: "TECH_ERROR", 4: "HANDOFF_HUMAN"}
    with pytest.raises(kappa.AnnotationError, match="thiếu id"):
        kappa.build_report(_ITEMS, kappa.load_annotations(tmp_path / "a.csv"), full, sources={})


def test_phieu_mu_khong_lo_nhan_vang(tmp_path: Path):
    kappa.make_sheets(_ITEMS, tmp_path)
    content = (tmp_path / "dev_a.csv").read_text(encoding="utf-8-sig")
    assert "PRICING_POLICY" not in content and "GREETING" not in content
    # Thứ tự xáo trộn, khác nhau giữa hai người — vị trí câu không được lộ nhãn
    many = [{"id": i, "text": f"câu {i}", "intent": "GREETING"} for i in range(1, 41)]
    kappa.make_sheets(many, tmp_path / "m")
    ids_a = (tmp_path / "m" / "dev_a.csv").read_text(encoding="utf-8-sig").splitlines()[1:]
    ids_b = (tmp_path / "m" / "dev_b.csv").read_text(encoding="utf-8-sig").splitlines()[1:]
    assert [r.split(",")[0] for r in ids_a] != [str(i) for i in range(1, 41)]
    assert ids_a != ids_b and sorted(ids_a) == sorted(ids_b)
    # Chạy lần hai không ghi đè phiếu đã có
    (tmp_path / "dev_a.csv").write_text("da gan nhan", encoding="utf-8")
    kappa.make_sheets(_ITEMS, tmp_path)
    assert (tmp_path / "dev_a.csv").read_text(encoding="utf-8") == "da gan nhan"
