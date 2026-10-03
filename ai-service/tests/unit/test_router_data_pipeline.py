"""Kiểm thử tính toàn vẹn của tập dữ liệu huấn luyện UC022 và chỉ số Cohen's Kappa."""

import hashlib
import json
from collections import Counter
from pathlib import Path


def test_intent_train_raw_distribution():
    """Kiểm tra tập train thô có đúng 3.000 mẫu và chuẩn phân bổ 6 văn phong."""
    raw_path = Path("data/intent_train_raw.jsonl")
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
    dedup_path = Path("data/intent_train_dedup.jsonl")
    assert dedup_path.exists(), "Không tìm thấy data/intent_train_dedup.jsonl"

    records = []
    with open(dedup_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Tỉ lệ loại bỏ phải nằm trong khoảng 25% - 40% (khớp đặc tả khoảng 30% bản sao)
    raw_count = 3000
    clean_count = len(records)
    removed_count = raw_count - clean_count
    dedup_rate = (removed_count / raw_count) * 100

    assert 20.0 <= dedup_rate <= 40.0, f"Tỉ lệ khử trùng lặp bất thường: {dedup_rate:.2f}%"

    # Xác thực mã hash trong artifacts/DATA_HASHES.txt
    file_hash = hashlib.sha256(dedup_path.read_bytes()).hexdigest()
    hashes_path = Path("artifacts/DATA_HASHES.txt")
    assert hashes_path.exists()
    assert f"data/intent_train_dedup.jsonl:{file_hash}" in hashes_path.read_text(encoding="utf-8")


def test_cohens_kappa_evaluation():
    """Kiểm tra chỉ số Cohen's Kappa đạt chuẩn Almost Perfect Agreement (>= 0.85)."""
    report_path = Path("reports/eval/annotation_kappa_report.json")
    assert report_path.exists(), "Không tìm thấy reports/eval/annotation_kappa_report.json"

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["sample_count"] == 200
    assert data["cohens_kappa"] >= 0.85, f"Chỉ số Kappa chưa đạt: {data['cohens_kappa']}"
    assert data["disagreed_count"] == 13
    assert len(data["disagreements"]) == 13
