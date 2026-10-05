#!/usr/bin/env python3
"""[R&D] Gán nhãn ý định bằng bàn phím — điền phiếu mù cho Cohen's Kappa (UC022 1/4).

    python scripts/label_intents.py dev_b      # Dev B
    python scripts/label_intents.py dev_a      # Dev A

Mỗi lần hiện MỘT câu. Bấm 1–7 để chọn nhãn · z = sửa câu vừa làm · q = nghỉ (lần sau chạy lại
là làm tiếp từ chỗ dừng). Lưu ngay sau mỗi câu vào ``data/annotations/<tên>.csv``.

Công cụ CHỈ đọc phiếu mù (id + câu). Nó không bao giờ mở ``data/intent_test_human.jsonl``
(đáp án) — người gán nhãn cũng không được mở file đó.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

LABELS = [
    ("GREETING", "chào hỏi, cảm ơn, tạm biệt"),
    ("KB_SEARCH", "hỏi thông tin, cách dùng, tính năng"),
    ("PRICING_POLICY", "hỏi giá, gói cước, khuyến mãi"),
    ("COMPLAINT_SUPPORT", "phàn nàn, không hài lòng"),
    ("HANDOFF_HUMAN", "muốn gặp người thật"),
    ("TECH_ERROR", "báo hệ thống lỗi, không dùng được"),
    ("BUYING_INTENT", "muốn mua, đăng ký, nâng cấp ngay"),
]


def read_key() -> str:
    """Một phím, không cần Enter, khi chạy trong cửa sổ terminal Windows; ngược lại (macOS/Linux,
    hoặc đầu vào bị chuyển hướng) thì đọc một dòng — gõ rồi Enter."""
    if sys.stdin.isatty():
        try:
            import msvcrt

            return msvcrt.getwch().lower()
        except ImportError:
            pass
    line = sys.stdin.readline()
    if not line:  # hết đầu vào — coi như nghỉ, không treo
        return "q"
    return (line.strip()[:1] or " ").lower()


def load(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames), list(reader)


def save(path: Path, fields: list[str], rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)  # ghi file tạm rồi đổi tên — tắt ngang cũng không hỏng phiếu


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("dev_a", "dev_b"):
        print("Dùng: python scripts/label_intents.py dev_a|dev_b")
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    path = Path("data/annotations") / f"{argv[0]}.csv"
    if not path.exists():
        print(f"Không có {path}. Chạy: python scripts/compute_annotation_kappa.py --make-sheets")
        return 1

    fields, rows = load(path)
    history: list[int] = []
    menu = "\n".join(f"  {i + 1}  {name:<18} {desc}" for i, (name, desc) in enumerate(LABELS))

    while True:
        todo = [i for i, r in enumerate(rows) if not (r.get("intent") or "").strip()]
        done = len(rows) - len(todo)
        if not todo:
            print(f"\nXONG! Đã gán nhãn {done}/{len(rows)} câu, lưu ở {path}.")
            return 0
        i = todo[0]
        print("\n" + "─" * 70)
        print(f"Câu {done + 1}/{len(rows)}   (z = sửa câu trước · q = nghỉ, lần sau làm tiếp)\n")
        print(f"   «  {rows[i]['text']}  »\n")
        print(menu)
        print("\nKhách nhắn câu này để làm gì? Bấm 1–7: ", end="", flush=True)

        key = read_key()
        if key == "q":
            print(f"\nĐã lưu {done}/{len(rows)} câu. Chạy lại lệnh để làm tiếp.")
            return 0
        if key == "z":
            if history:
                rows[history.pop()]["intent"] = ""
                save(path, fields, rows)
                print("\n↩  Đã xoá nhãn câu trước, làm lại câu đó.")
            continue
        if key in "1234567" and key:
            label = LABELS[int(key) - 1][0]
            rows[i]["intent"] = label
            history.append(i)
            save(path, fields, rows)
            print(label)
        else:
            print("\nChỉ bấm 1–7, z hoặc q.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
