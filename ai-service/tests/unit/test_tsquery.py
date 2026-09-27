"""``build_tsquery`` — ``src/ai/rag/tsquery.py``. Cổng ra Ngày 4 (2/2).

Chỉ kiểm CHUỖI sinh ra. Việc chuỗi đó khớp đúng đoạn nào trên Postgres thật (bỏ dấu, liền kề,
OR) nằm ở ``tests/integration/test_tim_khong_dau.py``.
"""

import re

import pytest

from src.ai.rag.tsquery import build_tsquery


def test_cau_khong_dau():
    """Câu không dấu: pyvi không ghép được từ nên mỗi âm tiết một toán hạng, nối bằng OR."""
    assert build_tsquery("chinh sach doi tra") == "chinh | sach | doi | tra"


def test_cau_khong_dau_kieu_tin_nhan():
    assert build_tsquery("shop giao trong ngay dc ko") == "shop | giao | trong | ngay | dc | ko"


def test_tu_ghep_co_dau_dung_lien_ke():
    q = build_tsquery("Chính sách đổi trả laptop như thế nào?")
    assert q == "(chính <-> sách) | đổi | trả | laptop | như | (thế <-> nào)"


def test_or_giua_cac_tu_khong_bao_gio_and():
    """AND trả rỗng ngay khi khách gõ thừa một từ — toán tử & không được xuất hiện."""
    q = build_tsquery("bảo hành máy lọc nước bao lâu")
    assert "&" not in q
    assert " | " in q


@pytest.mark.parametrize(
    ("cau_hoi", "toan_hang"),
    [
        ("NH-TL256I giá bao nhiêu", "nh-tl256i"),  # pyvi cắt thành "NH - TL256I"
        ("giá 6.790.000đ", "6.790.000đ"),
        ("khuyến mãi tháng 10/2026", "10/2026"),
    ],
)
def test_ma_va_so_giu_nguyen_cho_postgres_tach(cau_hoi, toan_hang):
    assert toan_hang in build_tsquery(cau_hoi).split(" | ")


def test_loc_sach_toan_tu_tsquery():
    """Câu hỏi là dữ liệu không đáng tin: không ký tự cú pháp nào được lọt vào làm toán tử."""
    q = build_tsquery("a & b | !c (d) :* <-> 'x' \\ \"y\"")
    assert q == "a | b | c | d | x | y"
    # Mọi thứ ngoài toán hạng chỉ còn " | ", "(", ")", " <-> " do chính hàm sinh ra.
    assert not re.search(r"[&!:*'\"\\]", q)


@pytest.mark.parametrize("rong", ["", "   ", "?!...", "\u200b\u200b", "- - -"])
def test_khong_con_am_tiet_thi_tra_none(rong):
    assert build_tsquery(rong) is None


def test_bo_trung_giu_thu_tu():
    assert build_tsquery("Giá giá GIÁ") == "giá"
    assert build_tsquery("tủ lạnh nào rẻ, tủ lạnh nào tốt") == "(tủ <-> lạnh) | nào | rẻ | tốt"


def test_chuan_hoa_truoc_khi_tach():
    """Câu hỏi đi qua CÙNG ``normalize_vi`` với tài liệu: dấu kiểu mới, U+200B, NFD đều hết."""
    assert build_tsquery("thuỷ\u200b tinh") == build_tsquery("thủy tinh")
