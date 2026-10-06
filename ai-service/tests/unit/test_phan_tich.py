"""Trích xuất có cấu trúc trên tệp mẫu THẬT — ``phan_tich.py`` và ``tien_trinh.py``.

Chạy trên ``data/kb_samples/`` (20 tệp hợp lệ + 1 PDF scan). Không chạm mạng hay CSDL.
"""

import csv
import io
import zipfile
from pathlib import Path

import pytest

from src.ai.exceptions import NoTextExtractedError, ParseFailedError, ParseTimeoutError
from src.ai.rag.ingest.phan_tich import phan_tich_tep
from src.ai.rag.ingest.tien_trinh import BoPhanTich

MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"
_MANIFEST = list(csv.DictReader(open(MAU / "manifest.csv", encoding="utf-8")))
HOP_LE = [
    (r["file"], r["dinh_dang"])
    for r in _MANIFEST
    if r["ma_http"] == "202" and r["file"] != "ban-scan-bao-hanh.pdf"
]


def test_manifest_co_du_20_tep_hop_le():
    assert len(HOP_LE) == 20


@pytest.mark.parametrize(("ten", "dinh_dang"), HOP_LE, ids=[t for t, _ in HOP_LE])
def test_moi_tep_hop_le_deu_trich_duoc_chu_va_heading(ten, dinh_dang):
    khoi = phan_tich_tep(MAU / ten, dinh_dang)
    assert any(k.loai != "heading" and k.text.strip() for k in khoi)
    # Heading là nguyên liệu trích dẫn của UC023 — tệp mẫu nào cũng có ít nhất tên tài liệu.
    assert any(k.loai == "heading" for k in khoi)


def test_pdf_scan_nem_parse_no_text_extracted():
    with pytest.raises(NoTextExtractedError) as loi:
        phan_tich_tep(MAU / "ban-scan-bao-hanh.pdf", "PDF")
    assert loi.value.code == "PARSE_NO_TEXT_EXTRACTED"


# ── PDF ──────────────────────────────────────────────────────────────────────


def test_pdf_heading_ba_cap_du_font_du_phong_khong_dam():
    """Chữ có dấu trong heading dùng font dự phòng KHÔNG đậm — vẫn phải nhận là heading."""
    heading = [(k.cap, k.text) for k in phan_tich_tep(MAU / "bang-gia-2026.pdf", "PDF")]
    heading = [h for h in heading if h[0]]
    assert (1, "Bảng giá sản phẩm 2026") in heading
    assert (2, "3. Máy lạnh") in heading
    assert (3, "6.1. Máy lọc nước") in heading


def test_pdf_bang_co_tieu_de_cot_va_ma_lien_mach():
    bang = [k for k in phan_tich_tep(MAU / "bang-gia-2026.pdf", "PDF") if k.loai == "bang"]
    tu_lanh = next(b for b in bang if "NH-TL180" in b.text)
    assert tu_lanh.text.split("\n")[0].startswith("Mã sản phẩm | Mô tả")
    assert "NH-TL380MD" in tu_lanh.text  # ô hẹp ngắt "NH-\nTL380MD" đã được nối lại
    assert tu_lanh.trang == 1


def test_pdf_so_trang_bat_dau_tu_1():
    trang = {k.trang for k in phan_tich_tep(MAU / "chinh-sach-bao-hanh.pdf", "PDF")}
    assert trang == {1, 2, 3}


def test_pdf_hong_nem_parse_failed(tmp_path):
    hong = tmp_path / "hong.pdf"
    hong.write_bytes(b"%PDF-1.7\n" + b"\x00rac" * 100)
    with pytest.raises(ParseFailedError):
        phan_tich_tep(hong, "PDF")


# ── DOCX / HTML / TXT ────────────────────────────────────────────────────────


def test_docx_heading_theo_style_va_bang_theo_thu_tu():
    khoi = phan_tich_tep(MAU / "chinh-sach-doi-tra.docx", "DOCX")
    assert khoi[0].loai == "heading" and khoi[0].cap == 1
    assert any(k.loai == "heading" and k.cap == 2 for k in khoi)
    # Bảng nằm đúng chỗ giữa các đoạn văn, không bị dồn xuống cuối.
    vi_tri_bang = [i for i, k in enumerate(khoi) if k.loai == "bang"]
    assert vi_tri_bang and vi_tri_bang[0] < len(khoi) - 1


def test_docx_hong_nem_parse_failed(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", b"<khong-phai-xml")
    hong = tmp_path / "hong.docx"
    hong.write_bytes(buf.getvalue())
    with pytest.raises(ParseFailedError):
        phan_tich_tep(hong, "DOCX")


def test_html_bo_nav_footer_script():
    khoi = phan_tich_tep(MAU / "khuyen-mai-thang-10.html", "HTML")
    tat_ca = "\n".join(k.text for k in khoi)
    goc = (MAU / "khuyen-mai-thang-10.html").read_text(encoding="utf-8")
    assert "<script" in goc and "<footer" in goc  # tiền đề: tệp có khung trang thật
    assert "function" not in tat_ca and "©" not in tat_ca
    assert khoi[0].loai == "heading" and "khuyến mãi tháng 10" in khoi[0].text.lower()
    assert any(k.loai == "bang" and "NH-TL256I" in k.text for k in khoi)


def test_html_khong_co_chu_nem_no_text(tmp_path):
    rong = tmp_path / "rong.html"
    rong.write_text("<html><head><style>p{}</style></head><body><script>x()</script></body></html>")
    with pytest.raises(NoTextExtractedError):
        phan_tich_tep(rong, "HTML")


def test_txt_heading_viet_hoa():
    khoi = phan_tich_tep(MAU / "faq-thanh-toan.txt", "TXT")
    heading = [(k.cap, k.text) for k in khoi if k.loai == "heading"]
    assert heading[0] == (1, "CÂU HỎI THƯỜNG GẶP VỀ THANH TOÁN")
    assert (2, "I. HÌNH THỨC THANH TOÁN") in heading


def test_md_bo_ky_hieu_nhan_manh():
    khoi = phan_tich_tep(MAU / "huong-dan-dat-hang-online.md", "MD")
    tat_ca = "\n".join(k.text for k in khoi)
    assert "**" not in tat_ca and "Chọn sản phẩm:" in tat_ca


# ── Tiến trình con ───────────────────────────────────────────────────────────


async def test_tien_trinh_con_tra_cung_ket_qua_va_ne_loi_qua_ranh_gioi():
    bo = BoPhanTich()
    try:
        khoi = await bo.phan_tich(MAU / "bang-gia-2026.pdf", "PDF", timeout_s=60)
        assert khoi == phan_tich_tep(MAU / "bang-gia-2026.pdf", "PDF")
        # Ngoại lệ đi qua pickle vẫn giữ đúng lớp và mã.
        with pytest.raises(NoTextExtractedError):
            await bo.phan_tich(MAU / "ban-scan-bao-hanh.pdf", "PDF", timeout_s=60)
    finally:
        bo.dong()


async def test_qua_gio_thi_giet_tien_trinh_con_va_dung_pool_moi():
    """Trần 1 ms: quá giờ chắc chắn. Tiến trình cũ phải bị GIẾT, lượt sau chạy trên pool mới.

    Test này cũng canh thuộc tính riêng ``_processes`` mà ``_giet_pool`` dựa vào — bản Python
    nào đổi tên nó thì test đỏ ở đây, không phải âm thầm để lại tiến trình treo.
    """
    bo = BoPhanTich()
    try:
        await bo.phan_tich(MAU / "faq-thanh-toan.txt", "TXT", timeout_s=60)  # khởi động pool
        tien_trinh_cu = list(bo._pool._processes.values())
        assert len(tien_trinh_cu) == 1  # đúng 1 worker

        with pytest.raises(ParseTimeoutError):
            await bo.phan_tich(MAU / "bang-gia-2026.pdf", "PDF", timeout_s=0.001)
        tien_trinh_cu[0].join(timeout=5)
        assert not tien_trinh_cu[0].is_alive()

        khoi = await bo.phan_tich(MAU / "bang-gia-2026.pdf", "PDF", timeout_s=60)
        assert khoi
    finally:
        bo.dong()
