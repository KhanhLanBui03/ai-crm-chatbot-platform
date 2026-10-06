"""Nhận diện định dạng thật bằng magic bytes — ``src/ai/rag/ingest/mime.py``.

Chỉ ghi tệp vào ``tmp_path``, không chạm mạng hay CSDL. Tệp "quá lớn" không cần 20 MiB thật:
truyền ``max_bytes`` nhỏ là đủ kiểm nhánh 413 — test chạy nhanh và repo không phình.
"""

import io
import zipfile
from pathlib import Path

import pytest

from src.ai.exceptions import FileTooLargeError, StoredFileNotFoundError, UnsupportedFormatError
from src.ai.rag.ingest.mime import nhan_dien_tep

GIOI_HAN = 20 * 1024 * 1024
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
VAN_BAN_VI = "Chính sách bảo hành: đổi trả trong 7 ngày.\n".encode()


def _ghi(tmp_path: Path, ten: str, noi_dung: bytes) -> Path:
    p = tmp_path / ten
    p.write_bytes(noi_dung)
    return p


def _zip(cac_tep: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for ten, noi_dung in cac_tep.items():
            z.writestr(ten, noi_dung)
    return buf.getvalue()


DOCX = _zip({"[Content_Types].xml": b"<Types/>", "word/document.xml": b"<w:document/>"})


# ── Nhận đúng ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("ten", "noi_dung", "source_type", "mime"),
    [
        ("bang-gia.pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", "PDF", "application/pdf"),
        (
            "bao-hanh.docx",
            DOCX,
            "DOCX",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("doi-tra.txt", VAN_BAN_VI, "TXT", "text/plain"),
        ("huong-dan.md", "# Hướng dẫn\n".encode(), "MD", "text/markdown"),
        ("faq.html", "<!doctype html><p>Câu hỏi</p>".encode(), "HTML", "text/html"),
        ("faq.htm", b"<p>ok</p>", "HTML", "text/html"),
    ],
)
def test_nhan_dung_nam_dinh_dang(tmp_path, ten, noi_dung, source_type, mime):
    kq = nhan_dien_tep(_ghi(tmp_path, ten, noi_dung), ten, GIOI_HAN)
    assert (kq.source_type, kq.mime_type, kq.size_bytes) == (source_type, mime, len(noi_dung))


def test_duoi_viet_hoa_van_nhan(tmp_path):
    p = _ghi(tmp_path, "BANG-GIA.PDF", b"%PDF-1.4\n")
    assert nhan_dien_tep(p, "BANG-GIA.PDF", GIOI_HAN).source_type == "PDF"


def test_pdf_co_rac_truoc_chu_ky_van_nhan(tmp_path):
    """Đặc tả PDF cho phép rác trong 1 024 byte đầu — vài trình xuất có làm vậy."""
    p = _ghi(tmp_path, "a.pdf", b"\x00" * 100 + b"%PDF-1.5\n")
    assert nhan_dien_tep(p, "a.pdf", GIOI_HAN).source_type == "PDF"


def test_chu_tieng_viet_bi_cat_ngang_o_bien_8kib_van_nhan(tmp_path):
    """Bẫy thật: 8 KiB đầu cắt đôi một chữ nhiều byte. Giải mã thường báo lỗi oan."""
    noi_dung = b"a" * (8 * 1024 - 1) + "ệ".encode()  # 'ệ' = 3 byte, chỉ 1 byte lọt vào vùng đọc
    p = _ghi(tmp_path, "dai.txt", noi_dung)
    assert nhan_dien_tep(p, "dai.txt", GIOI_HAN).source_type == "TXT"


def test_dung_bang_gioi_han_van_nhan(tmp_path):
    p = _ghi(tmp_path, "a.txt", b"x" * 100)
    assert nhan_dien_tep(p, "a.txt", max_bytes=100).size_bytes == 100


# ── 415: đuôi không nhận ─────────────────────────────────────────────────────


@pytest.mark.parametrize("ten", ["bang-gia.xlsx", "anh.png", "khong-duoi", "script.exe"])
def test_duoi_khong_ho_tro_415(tmp_path, ten):
    p = _ghi(tmp_path, "tep", VAN_BAN_VI)
    with pytest.raises(UnsupportedFormatError):
        nhan_dien_tep(p, ten, GIOI_HAN)


# ── 415: đuôi đúng, nội dung sai — đúng ca "sai MIME" của bộ 5 tệp lỗi ───────


@pytest.mark.parametrize(
    ("ten", "noi_dung"),
    [
        ("gia-mao.pdf", PNG),  # PNG đổi đuôi .pdf
        ("gia-mao.docx", _zip({"a.txt": b"x"})),  # ZIP thường đổi đuôi .docx
        ("gia-mao.docx", b"PK\x03\x04" + b"hong"),  # chữ ký ZIP nhưng ZIP hỏng
        ("gia-mao.docx", b"%PDF-1.7\n"),  # PDF đổi đuôi .docx
        ("nhi-phan.txt", PNG),  # nhị phân có NUL
        ("cp1258.txt", "Hàng hóa".encode("cp1258")),  # bảng mã cũ — chỉ nhận UTF-8
    ],
)
def test_noi_dung_khong_khop_duoi_415(tmp_path, ten, noi_dung):
    p = _ghi(tmp_path, ten, noi_dung)
    with pytest.raises(UnsupportedFormatError):
        nhan_dien_tep(p, ten, GIOI_HAN)


# ── 413 và thứ tự kiểm ───────────────────────────────────────────────────────


def test_vuot_gioi_han_413(tmp_path):
    p = _ghi(tmp_path, "a.txt", b"x" * 101)
    with pytest.raises(FileTooLargeError):
        nhan_dien_tep(p, "a.txt", max_bytes=100)


def test_qua_lon_va_sai_duoi_thi_413_truoc_415(tmp_path):
    """Khớp thứ tự của java-core: dung lượng trước, đuôi sau — hai tầng cùng trả một mã."""
    p = _ghi(tmp_path, "a.xlsx", b"x" * 101)
    with pytest.raises(FileTooLargeError):
        nhan_dien_tep(p, "a.xlsx", max_bytes=100)


# ── Tệp không tồn tại ────────────────────────────────────────────────────────


def test_khong_co_tep(tmp_path):
    with pytest.raises(StoredFileNotFoundError):
        nhan_dien_tep(tmp_path / "khong-co.pdf", "khong-co.pdf", GIOI_HAN)


def test_duong_dan_la_thu_muc(tmp_path):
    with pytest.raises(StoredFileNotFoundError):
        nhan_dien_tep(tmp_path, "a.pdf", GIOI_HAN)
