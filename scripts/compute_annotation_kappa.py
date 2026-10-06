#!/usr/bin/env python3
"""[R&D] Cohen's Kappa giữa hai người gán nhãn ĐỘC LẬP trên 200 câu test người thật (UC022 1/4).

Script này KHÔNG sinh nhãn. Nó chỉ đọc nhãn mà từng người tự gán vào file riêng của mình,
rồi đối chiếu. Thiếu file thì dừng với lỗi — không bao giờ tự điền nhãn để "ra số".

QUY TRÌNH (đặc tả kế hoạch 21 ngày, Ngày 3)
-------------------------------------------
1. Tạo phiếu gán nhãn MÙ — chỉ có id và câu, không có nhãn vàng::

       python scripts/compute_annotation_kappa.py --make-sheets

   Sinh ``data/annotations/dev_a.csv`` và ``data/annotations/dev_b.csv``.

2. Mỗi người mở file CỦA MÌNH (Excel được), điền cột ``intent`` bằng một trong 7 nhãn.
   KHÔNG xem file của người kia, KHÔNG xem ``data/intent_test_human.jsonl``.

3. Tính Kappa::

       python scripts/compute_annotation_kappa.py

   Ghi ``reports/eval/annotation_kappa_report.json``. Các ca bất đồng được liệt kê kèm
   nhãn vàng hiện tại để buổi họp thống nhất xem lại.

Nhãn vàng trong ``data/intent_test_human.jsonl`` là tập test ĐÃ ĐÓNG BĂNG: script chỉ đọc,
không bao giờ ghi vào đó.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

INTENTS = [
    "GREETING",
    "KB_SEARCH",
    "PRICING_POLICY",
    "COMPLAINT_SUPPORT",
    "HANDOFF_HUMAN",
    "TECH_ERROR",
    "BUYING_INTENT",
]

TEST_PATH = Path("data/intent_test_human.jsonl")
ANNOT_DIR = Path("data/annotations")
ANNOTATORS = {
    "dev_a": "Dev A (Platform / Java Core)",
    "dev_b": "Dev B (AI Service / Python)",
}
REPORT_PATH = Path("reports/eval/annotation_kappa_report.json")
SHEET_SEED = 42


class AnnotationError(Exception):
    """Phiếu gán nhãn thiếu, sai định dạng hoặc chưa điền đủ."""


def load_test_set(path: Path = TEST_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def make_sheets(test_items: list[dict], out_dir: Path = ANNOT_DIR) -> list[Path]:
    """Phiếu mù cho từng người: id + câu, cột intent để trống. Không ghi đè phiếu đã có."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for key in ANNOTATORS:
        path = out_dir / f"{key}.csv"
        if path.exists():
            print(f"BỎ QUA {path}: đã tồn tại — không ghi đè nhãn người đã gán")
            continue
        # Tập test xếp theo nhãn (28 câu đầu đều GREETING) — giữ thứ tự đó là lộ nhãn qua vị
        # trí. Xáo trộn với seed cố định, mỗi người một thứ tự khác nhau.
        order = list(test_items)
        random.Random(f"{SHEET_SEED}-{key}").shuffle(order)
        # utf-8-sig để Excel trên Windows mở đúng tiếng Việt
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "text", "intent"])
            for item in order:
                w.writerow([item["id"], item["text"], ""])
        written.append(path)
    return written


def load_annotations(path: Path) -> dict[int, str]:
    """Đọc phiếu .csv hoặc .jsonl thành {id: intent}. Kiểm tra từng dòng, không đoán."""
    if not path.exists():
        raise AnnotationError(f"Không có phiếu {path}. Chạy --make-sheets rồi gán nhãn trước.")

    rows: list[dict] = []
    if path.suffix == ".csv":
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    elif path.suffix == ".jsonl":
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    else:
        raise AnnotationError(f"{path}: chỉ nhận .csv hoặc .jsonl")

    labels: dict[int, str] = {}
    for n, row in enumerate(rows, start=2):
        intent = (row.get("intent") or "").strip().upper()
        if not intent:
            raise AnnotationError(f"{path} dòng {n}: chưa điền intent (id={row.get('id')})")
        if intent not in INTENTS:
            raise AnnotationError(f"{path} dòng {n}: nhãn {intent!r} không thuộc 7 nhãn {INTENTS}")
        item_id = int(row["id"])
        if item_id in labels:
            raise AnnotationError(f"{path} dòng {n}: id {item_id} bị lặp")
        labels[item_id] = intent
    return labels


def _find_sheet(key: str, ann_dir: Path) -> Path:
    for ext in (".csv", ".jsonl"):
        if (ann_dir / f"{key}{ext}").exists():
            return ann_dir / f"{key}{ext}"
    return ann_dir / f"{key}.csv"


def cohens_kappa(a: list[str], b: list[str], categories: list[str] = INTENTS) -> dict:
    """Cohen's Kappa cho hai chuỗi nhãn cùng độ dài. Thuần Python để dễ đối chiếu công thức."""
    if len(a) != len(b) or not a:
        raise ValueError("Hai chuỗi nhãn phải cùng độ dài và khác rỗng")
    n = len(a)
    agree = sum(x == y for x, y in zip(a, b, strict=True))
    p_o = agree / n
    ca, cb = Counter(a), Counter(b)
    p_e = sum((ca[c] / n) * (cb[c] / n) for c in categories)
    # p_e = 1 chỉ khi cả hai người dùng đúng một nhãn duy nhất cho mọi câu — Kappa không xác định
    kappa = (p_o - p_e) / (1.0 - p_e) if p_e < 1.0 else float("nan")
    return {"n": n, "agreed": agree, "p_o": p_o, "p_e": p_e, "kappa": kappa}


def interpret(kappa: float) -> str:
    """Thang Landis & Koch (1977)."""
    if kappa != kappa:  # NaN
        return "Không xác định"
    for lo, name in [
        (0.81, "Almost Perfect"), (0.61, "Substantial"), (0.41, "Moderate"),
        (0.21, "Fair"), (0.0, "Slight"),
    ]:
        if kappa >= lo:
            return f"{name} Agreement (Landis & Koch, 1977)"
    return "Poor Agreement (Landis & Koch, 1977)"


def build_report(test_items: list[dict], labels_a: dict[int, str], labels_b: dict[int, str],
                 sources: dict[str, str]) -> dict:
    ids = [item["id"] for item in test_items]
    for name, labels in (("dev_a", labels_a), ("dev_b", labels_b)):
        missing = sorted(set(ids) - set(labels))
        extra = sorted(set(labels) - set(ids))
        if missing or extra:
            raise AnnotationError(
                f"Phiếu {name} không khớp tập test: thiếu id {missing[:10]}, thừa id {extra[:10]}"
            )

    a = [labels_a[i] for i in ids]
    b = [labels_b[i] for i in ids]
    k = cohens_kappa(a, b)

    # Hàng = Dev A, cột = Dev B
    matrix = {r: {c: 0 for c in INTENTS} for r in INTENTS}
    for x, y in zip(a, b, strict=True):
        matrix[x][y] += 1

    by_id = {item["id"]: item for item in test_items}
    gold = [by_id[i]["intent"] for i in ids]
    disagreements = [
        {
            "id": i,
            "text": by_id[i]["text"],
            "dev_a": la,
            "dev_b": lb,
            # Để buổi họp thống nhất đối chiếu — KHÔNG dùng để tính Kappa
            "current_gold": by_id[i]["intent"],
        }
        for i, la, lb in zip(ids, a, b, strict=True)
        if la != lb
    ]

    return {
        "annotator_1": ANNOTATORS["dev_a"],
        "annotator_2": ANNOTATORS["dev_b"],
        "sources": sources,
        "sample_count": k["n"],
        "agreed_count": k["agreed"],
        "disagreed_count": len(disagreements),
        "observed_agreement_po": round(k["p_o"], 4),
        "chance_agreement_pe": round(k["p_e"], 4),
        "cohens_kappa": round(k["kappa"], 4),
        "interpretation": interpret(k["kappa"]),
        "agreement_with_gold": {
            "dev_a": round(sum(x == g for x, g in zip(a, gold, strict=True)) / len(ids), 4),
            "dev_b": round(sum(y == g for y, g in zip(b, gold, strict=True)) / len(ids), 4),
        },
        "confusion_matrix_rows_dev_a_cols_dev_b": matrix,
        "disagreements": disagreements,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--make-sheets", action="store_true", help="tạo phiếu gán nhãn mù rồi thoát")
    ap.add_argument("--annotations-dir", type=Path, default=ANNOT_DIR)
    ap.add_argument("--out", type=Path, default=REPORT_PATH)
    args = ap.parse_args(argv)

    test_items = load_test_set()

    if args.make_sheets:
        for p in make_sheets(test_items, args.annotations_dir):
            print(f"Đã tạo phiếu mù: {p}")
        return 0

    try:
        path_a = _find_sheet("dev_a", args.annotations_dir)
        path_b = _find_sheet("dev_b", args.annotations_dir)
        report = build_report(
            test_items,
            load_annotations(path_a),
            load_annotations(path_b),
            sources={"dev_a": str(path_a), "dev_b": str(path_b)},
        )
    except AnnotationError as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cohen's Kappa κ = {report['cohens_kappa']} — {report['interpretation']}")
    print(f"Đồng thuận {report['agreed_count']}/{report['sample_count']}, "
          f"bất đồng {report['disagreed_count']} ca -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
