"""``normalize_vi`` — ``src/ai/rag/chuan_hoa.py``. Cổng ra Ngày 4 (1/2).

Hàm này chạy ở CẢ HAI đầu (nạp tài liệu và câu hỏi). Mỗi ca dưới đây là một cách hai chuỗi
"trông giống nhau" mà khác nhau từng byte — không chuẩn hoá thì làn từ khoá không khớp và vector
nhúng lệch, mà không có lỗi nào báo ra.
"""

import unicodedata
from pathlib import Path

import pytest

from src.ai.rag.chuan_hoa import normalize_vi

MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"


# ── Mã hoá: NFC và ký tự vô hình ─────────────────────────────────────────────


def test_nfd_thanh_nfc():
    nfd = unicodedata.normalize("NFD", "Chính sách bảo hành")
    assert nfd != "Chính sách bảo hành"  # tiền đề: khác nhau từng byte
    assert normalize_vi(nfd) == "Chính sách bảo hành"


@pytest.mark.parametrize("vo_hinh", ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad"])
def test_bo_ky_tu_vo_hinh(vo_hinh):
    assert normalize_vi(f"NỒI{vo_hinh} CHIÊN") == "NỒI CHIÊN"


def test_bo_ky_tu_dieu_khien_nhung_giu_xuong_dong():
    assert normalize_vi("dòng 1\x00\x07\ndòng 2") == "dòng 1\ndòng 2"


# ── Vị trí dấu thanh: kiểu mới → kiểu cũ ─────────────────────────────────────


@pytest.mark.parametrize(
    ("dau_vao", "mong_doi"),
    [
        ("hoà bình", "hòa bình"),
        ("HOÀ", "HÒA"),
        ("khoẻ mạnh", "khỏe mạnh"),
        ("thuỷ tinh", "thủy tinh"),
        ("tuỳ chọn", "tùy chọn"),
        ("hoá đơn", "hóa đơn"),
    ],
)
def test_dua_dau_ve_kieu_cu(dau_vao, mong_doi):
    assert normalize_vi(dau_vao) == mong_doi


@pytest.mark.parametrize(
    "khong_doi",
    [
        "quý khách",  # "qu" là phụ âm — dấu trên y đúng ở cả hai kiểu
        "hoặc",  # a còn dấu trăng — không phải "oa" trần
        "hoàng",  # có phụ âm cuối — hai kiểu đặt dấu giống nhau
        "khuỷu tay",  # "uyu" không phải "uy" cuối âm tiết
        "ngoái lại",  # "oai" — dấu đã đúng chỗ
        "khuyến mãi",
    ],
)
def test_khong_dung_am_tiet_dat_dau_giong_nhau(khong_doi):
    assert normalize_vi(khong_doi) == khong_doi


def test_hai_kieu_go_thanh_mot_chuoi():
    """Điều kiện cần của "một hàm cho hai đầu": tài liệu và câu hỏi gõ khác kiểu vẫn bằng nhau."""
    tai_lieu = unicodedata.normalize("NFD", "Bình thuỷ tinh hoà tan")
    cau_hoi = "bình thủy tinh hòa tan"
    assert normalize_vi(tai_lieu).lower() == normalize_vi(cau_hoi)


# ── Ký tự lặp ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("dau_vao", "mong_doi"),
    [
        ("đẹppppp", "đẹp"),
        ("quáaaa", "quá"),  # so theo chữ gốc ở NFD — không thành "quáa"
        ("hoàaaa", "hòa"),
        ("sao vậy???", "sao vậy?"),
        ("tuyệt!!!", "tuyệt!"),
    ],
)
def test_gop_ky_tu_lap(dau_vao, mong_doi):
    assert normalize_vi(dau_vao) == mong_doi


@pytest.mark.parametrize(
    "khong_doi",
    [
        "1.000.000đ",  # chữ số không bao giờ bị gộp
        "www.nganha.vn",  # w không thuộc bảng chữ cái tiếng Việt
        "mục (iii)",  # chữ số La Mã thường
        "Chương III",  # chữ HOA không bị gộp
        "cỡ XXXL",
        "xoong nồi",  # chữ đôi là hợp lệ
    ],
)
def test_khong_gop_nham(khong_doi):
    assert normalize_vi(khong_doi) == khong_doi


# ── Khoảng trắng ─────────────────────────────────────────────────────────────


def test_gop_khoang_trang_ngang():
    assert normalize_vi("a\u00a0\u00a0b\tc   d") == "a b c d"


def test_giu_xuong_dong_toi_da_mot_dong_trong():
    assert normalize_vi("  dòng 1  \r\n\r\n\n\n  dòng 2 \r") == "dòng 1\n\ndòng 2"


# ── Tính chất ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "van_ban",
    ["hoà\u200b  bình!!!", unicodedata.normalize("NFD", "thuỷ tinh đẹppp"), "  \n\n\n x \t y "],
)
def test_luy_dang(van_ban):
    mot_lan = normalize_vi(van_ban)
    assert normalize_vi(mot_lan) == mot_lan


def test_khong_ha_chu_thuong_khong_bo_dau():
    """Hạ chữ thường và bỏ dấu là việc của SQL (V210) — ở đây mà làm là hỏng nội dung hiển thị."""
    assert normalize_vi("Bảng Giá NH-TL256I") == "Bảng Giá NH-TL256I"


def test_tep_mau_ban_co_chu_dich():
    """``huong-dan-bao-quan-noi-chien.txt``: NFD + 8 ký tự U+200B + trộn hoà/hòa, thuỷ/thủy."""
    tho = (MAU / "huong-dan-bao-quan-noi-chien.txt").read_text(encoding="utf-8")
    assert tho.count("\u200b") == 8 and not unicodedata.is_normalized("NFC", tho)

    sach = normalize_vi(tho)
    assert "\u200b" not in sach
    assert unicodedata.is_normalized("NFC", sach)
    assert "thuỷ" not in sach and "thủy" in sach
    assert " hoà " not in sach
