"""Công cụ cho bộ vàng Ngày 6 — mục lục để viết câu hỏi, bản đoạn để gán căn cứ, kiểm tệp. [R&D]

    cd ai-service && source .venv/bin/activate
    python -m tests.eval.bo_vang muc-luc > muc_luc.md   # đầu vào DUY NHẤT khi viết câu hỏi
    python -m tests.eval.bo_vang doan    > doan.md      # người gán đọc để tìm câu trích
    python -m tests.eval.bo_vang kiem                   # mặc định tests/eval/golden_set.jsonl

Không cần CSDL, không cần vector: đoạn được dựng bằng CHÍNH đường ống nạp (``phan_tich_tep`` →
``normalize_vi`` → ``chia_doan``) trên ``data/kb_samples/``, nên nội dung trùng từng ký tự với
cột ``content`` mà worker ghi vào ``knowledge.knowledge_chunks``.

VÌ SAO NGƯỜI VIẾT CÂU HỎI CHỈ ĐƯỢC THẤY MỤC LỤC
-----------------------------------------------
Mô hình ngôn ngữ nhìn đoạn văn rồi đặt câu hỏi thì chép lại từ ngữ của đoạn. Làn từ khoá hưởng
lợi, và phép so dense ↔ sparse ↔ hybrid của Ngày 6 lệch đúng về phía đang bị đo. Mục lục chỉ
có tiêu đề tài liệu và heading — đủ để biết kho nói về gì, không đủ để chép câu chữ.

Heading dạng câu hỏi (kết thúc bằng "?") bị ẩn: ở ``faq-bao-hanh.html`` chính heading là câu
hỏi mẫu, đưa vào thì câu hỏi sinh ra chép nguyên văn.

ĐỊNH DẠNG MỘT DÒNG CỦA ``golden_set.jsonl``
-------------------------------------------
::

    {"id": "G001",
     "question": "tủ lạnh inverter hư máy nén sau 3 năm còn bảo hành ko",
     "can_cu": [
        {"file": "chinh-sach-bao-hanh.pdf", "quote": "máy nén của tủ lạnh inverter"},
        {"file": "faq-bao-hanh.html", "quote": "riêng máy nén được bảo hành đến 10 năm"}],
     "loai": "dieu_kien", "kieu_go": "viet_tat"}

- ``can_cu`` là các căn cứ TƯƠNG ĐƯƠNG — lọt top-5 MỘT trong số đó là trúng. Gán ĐỦ mọi chỗ chứa
  đáp án (bản PDF, bản hỏi đáp, bản tiếng Anh), thiếu thì hệ truy hồi bị phạt oan.
- ``can_cu: []`` = kho không có đáp án. Giữ lại cho UC025 (từ chối), KHÔNG tính vào recall@5.
- Gán theo (tệp + câu trích), KHÔNG theo ``chunk_id``: UUID đổi mỗi lần nạp lại.
- Câu trích so sau ``normalize_vi`` + gộp khoảng trắng + không phân biệt hoa thường, phải nằm
  trong ĐÚNG MỘT đoạn của tệp đó. Khớp 0 hay ≥ 2 đoạn đều là lỗi.
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Collection
from pathlib import Path

from src.ai.exceptions import AiServiceError
from src.ai.rag.chuan_hoa import normalize_vi
from src.ai.rag.ingest.chia_doan import Doan, chia_doan
from src.ai.rag.ingest.duong_ong import chuan_hoa_khoi
from src.ai.rag.ingest.phan_tich import phan_tich_tep

MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"
BO_VANG = Path(__file__).resolve().parent / "golden_set.jsonl"

# Bản 1 đã bị chinh-sach-doi-tra-v2.md thay. Lúc đo, bản 1 ở trạng thái ARCHIVED — không vào
# mục lục, không được làm căn cứ.
TEP_BI_THAY = {"chinh-sach-doi-tra.docx"}

# Câu trích ngắn hơn thế này dễ khớp nhầm sang đoạn khác chỉ vì trùng vài chữ thông dụng.
SO_TU_TOI_THIEU = 5


class KhoMau:
    """Mọi tệp nhận 202 và có chữ trong ``manifest.csv``, giữ thứ tự manifest. ``chi_tep`` giới
    hạn vào vài tệp — cho test, để khỏi phân tích cả 19 tệp."""

    def __init__(self, chi_tep: Collection[str] | None = None) -> None:
        self.tieu_de: dict[str, str] = {}
        self.ngon_ngu: dict[str, str] = {}
        self.dinh_dang: dict[str, str] = {}
        self.doan: dict[str, list[Doan]] = {}
        for r in csv.DictReader(open(MAU / "manifest.csv", encoding="utf-8")):
            if r["ma_http"] != "202" or (chi_tep is not None and r["file"] not in chi_tep):
                continue
            try:
                khoi = phan_tich_tep(MAU / r["file"], r["dinh_dang"])
            except AiServiceError:
                continue  # PDF scan — không có chữ thì không làm căn cứ được
            self.doan[r["file"]] = chia_doan(chuan_hoa_khoi(khoi))
            self.tieu_de[r["file"]] = r["title"]
            self.ngon_ngu[r["file"]] = r["language"]
            self.dinh_dang[r["file"]] = r["dinh_dang"]


def de_so(chu: str) -> str:
    """Dạng so khớp: ``normalize_vi`` + gộp khoảng trắng + bỏ phân biệt hoa thường."""
    return " ".join(normalize_vi(chu).split()).casefold()


def in_muc_luc(kho: KhoMau) -> None:
    print("# Mục lục kho tri thức\n")
    for tep, cac_doan in kho.doan.items():
        if tep in TEP_BI_THAY:
            continue
        nhan_en = " (tài liệu tiếng Anh)" if kho.ngon_ngu[tep] == "en" else ""
        print(f"## {kho.tieu_de[tep]}{nhan_en}\n")
        da_in: set[tuple[str, ...]] = set()
        for d in cac_doan:
            if not d.heading:
                continue
            # Bỏ cấp gốc (trùng tiêu đề tài liệu) và mọi cấp dạng câu hỏi.
            cac_cap = [h for h in d.heading.split(" > ")[1:] if not h.rstrip().endswith("?")]
            for sau in range(1, len(cac_cap) + 1):
                nhanh = tuple(cac_cap[:sau])
                if nhanh not in da_in:
                    da_in.add(nhanh)
                    print(f"{'  ' * (sau - 1)}- {nhanh[-1]}")
        print()


def in_doan(kho: KhoMau) -> None:
    print("# Toàn bộ đoạn theo tệp — để tìm câu trích\n")
    for tep, cac_doan in kho.doan.items():
        bi_thay = " — ⚠️ ĐÃ BỊ THAY, không dùng làm căn cứ" if tep in TEP_BI_THAY else ""
        print(f"## `{tep}` — {kho.tieu_de[tep]} ({len(cac_doan)} đoạn){bi_thay}\n")
        for d in cac_doan:
            trang = f" · trang {d.page_number}" if d.page_number else ""
            print(f"### [{d.chunk_index}] {d.heading or '(không heading)'}{trang}\n")
            print(d.content, "\n")


def kiem(kho: KhoMau, duong_dan: Path) -> int:
    """In lỗi + thống kê. Trả mã thoát: 0 khi sạch lỗi."""
    da_so = {tep: [de_so(d.content) for d in ds] for tep, ds in kho.doan.items()}
    loi: list[str] = []
    ids: set[str] = set()
    cau_da_co: set[str] = set()
    theo_tep: Counter[str] = Counter()
    theo_loai: Counter[str] = Counter()
    theo_kieu_go: Counter[str] = Counter()
    co_dap_an = khong_dap_an = 0

    for so_dong, dong in enumerate(duong_dan.read_text(encoding="utf-8").splitlines(), 1):
        if not dong.strip():
            continue
        try:
            m = json.loads(dong)
        except json.JSONDecodeError as e:
            loi.append(f"dòng {so_dong}: JSON hỏng — {e}")
            continue
        thieu = {"id", "question", "can_cu"} - m.keys()
        if thieu:
            loi.append(f"dòng {so_dong}: thiếu trường {sorted(thieu)}")
            continue
        ma = m["id"]
        if ma in ids:
            loi.append(f"{ma}: trùng id")
        ids.add(ma)
        cau = de_so(m["question"])
        if not cau:
            loi.append(f"{ma}: câu hỏi rỗng")
        elif cau in cau_da_co:
            loi.append(f"{ma}: trùng câu hỏi với một dòng trước")
        cau_da_co.add(cau)
        theo_loai[m.get("loai", "?")] += 1
        theo_kieu_go[m.get("kieu_go", "?")] += 1

        if not m["can_cu"]:
            khong_dap_an += 1
            continue
        co_dap_an += 1
        for cc in m["can_cu"]:
            tep, trich = cc.get("file", ""), cc.get("quote", "")
            if tep in TEP_BI_THAY:
                loi.append(f"{ma}: {tep} đã bị thay bởi bản mới — không làm căn cứ")
                continue
            if tep not in da_so:
                loi.append(f"{ma}: không có tệp {tep!r} trong kho")
                continue
            if len(trich.split()) < SO_TU_TOI_THIEU:
                loi.append(f"{ma}: câu trích dưới {SO_TU_TOI_THIEU} từ — {trich!r}")
                continue
            khop = [i for i, c in enumerate(da_so[tep]) if de_so(trich) in c]
            if len(khop) != 1:
                loi.append(f"{ma}: câu trích khớp {len(khop)} đoạn {khop} của {tep} — {trich!r}")
                continue
            theo_tep[tep] += 1

    for dong_loi in loi:
        print(f"LỖI  {dong_loi}")
    print(f"\n{co_dap_an} câu có đáp án (mẫu số recall@5) · {khong_dap_an} câu không có đáp án\n")
    print("Căn cứ theo tệp (tệp 0 câu là lỗ hổng phủ):")
    for tep in kho.doan:
        if tep not in TEP_BI_THAY:
            print(f"  {theo_tep[tep]:>3}  {tep}")
    print(f"\nloai:    {dict(theo_loai.most_common())}")
    print(f"kieu_go: {dict(theo_kieu_go.most_common())}")
    print(f"\nsha256  {hashlib.sha256(duong_dan.read_bytes()).hexdigest()}  {duong_dan.name}")
    print("SẠCH" if not loi else f"{len(loi)} LỖI")
    return 0 if not loi else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    lenh = ap.add_subparsers(dest="lenh", required=True)
    lenh.add_parser("muc-luc", help="tiêu đề + heading, KHÔNG nội dung — để viết câu hỏi")
    lenh.add_parser("doan", help="toàn bộ đoạn theo tệp — để tìm câu trích")
    p_kiem = lenh.add_parser("kiem", help="kiểm golden_set.jsonl")
    p_kiem.add_argument("tep", nargs="?", type=Path, default=BO_VANG)
    args = ap.parse_args()

    kho = KhoMau()
    if args.lenh == "muc-luc":
        in_muc_luc(kho)
    elif args.lenh == "doan":
        in_doan(kho)
    else:
        sys.exit(kiem(kho, args.tep))


if __name__ == "__main__":
    main()
