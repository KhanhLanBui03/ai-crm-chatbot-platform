"""UC019 — chặng phân tích của ``service.nap_tai_lieu`` trên Postgres (RLS) và RustFS (S3) thật.

Cổng ra Ngày 4: PDF scan chuyển ``FAILED`` kèm ``error_message`` — mã lỗi thứ 5 của UC018
(``PARSE_NO_TEXT_EXTRACTED``), chỉ đo được khi có parser.

Ngày 4 viết các test này trên ``phan_tich_tai_lieu`` (dừng ở ``PROCESSING`` + đoạn trong bộ nhớ).
Ngày 5 thay hàm đó bằng ``nap_tai_lieu`` chạy tới ``READY`` (ADR-0021), nên test đọc đoạn từ
``knowledge_chunks`` thay vì từ bộ nhớ — cùng khẳng định, kiểm ở chỗ chặt hơn. Test của riêng
Ngày 5 (nhúng, chống trùng, thử lại, mất quyền, bộ quét, tiến độ) ở ``test_nap_tai_lieu.py``.

Luồng mỗi test: đưa tệp lên S3 dưới key của tenant → ghi dòng ``PENDING`` như UC018 → gọi
facade (mỗi chặng tự mở phiên, như worker gọi) → đọc lại trạng thái.
"""

import pytest

from src.ai.integrations import object_storage
from tests.integration.nap_chung import cac_doan, nap, tai_lieu_pending, trang_thai

# ── Cổng ra Ngày 4 ───────────────────────────────────────────────────────────


async def test_pdf_scan_chuyen_failed_kem_parse_no_text_extracted(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "ban-scan-bao-hanh.pdf", "PDF")

    ket_qua = await nap(factory, tenant_a, doc)

    assert (ket_qua.trang_thai, ket_qua.loi) == ("FAILED", "PARSE_NO_TEXT_EXTRACTED")
    status, loi, _, buoc = await trang_thai(factory, tenant_a, doc)
    assert status == "FAILED"
    assert loi.startswith("PARSE_NO_TEXT_EXTRACTED: ")
    assert "OCR" in loi  # câu cho người dùng biết cách sửa
    assert buoc == "EXTRACTING"  # SCR033 tô đỏ đúng bước hỏng
    assert await cac_doan(factory, tenant_a, doc) == []


# ── Luồng tốt ────────────────────────────────────────────────────────────────


async def test_pdf_tot_ra_doan_co_heading_va_trang(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "bang-gia-2026.pdf", "PDF")

    ket_qua = await nap(factory, tenant_a, doc)

    assert ket_qua.trang_thai == "READY"
    doan = await cac_doan(factory, tenant_a, doc)
    may_lanh = [d for d in doan if d.heading == "Bảng giá sản phẩm 2026 > 3. Máy lạnh"]
    assert may_lanh and may_lanh[0].page_number == 2
    assert "NH-ML09 |" in may_lanh[0].content
    assert [d.chunk_index for d in doan] == list(range(len(doan)))


async def test_noi_dung_da_chuan_hoa(ha_tang, kho_s3, tenant_a):
    """Tệp "bẩn có chủ đích" (NFD + U+200B + hoà/hòa): đoạn ra phải sạch như câu hỏi sẽ sạch."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(
        factory, kho_s3, tenant_a, "huong-dan-bao-quan-noi-chien.txt", "TXT"
    )
    await nap(factory, tenant_a, doc)
    doan = await cac_doan(factory, tenant_a, doc)
    tat_ca = "\n".join(d.content + (d.heading or "") for d in doan)
    assert tat_ca and "​" not in tat_ca and "thuỷ" not in tat_ca


# ── Chống nhận trùng và cô lập tenant ────────────────────────────────────────


async def test_goi_lan_hai_thi_bo_qua(ha_tang, kho_s3, tenant_a):
    """Kafka giao ít nhất một lần: lượt trùng tới sau không được nạp lại."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    assert (await nap(factory, tenant_a, doc)).trang_thai == "READY"
    so_doan = len(await cac_doan(factory, tenant_a, doc))
    assert (await nap(factory, tenant_a, doc)).trang_thai == "BO_QUA"
    assert len(await cac_doan(factory, tenant_a, doc)) == so_doan


async def test_tai_lieu_cua_tenant_khac_thi_bo_qua(ha_tang, kho_s3, tenant_a, tenant_b):
    """RLS: phiên tenant B không nhìn thấy — càng không nhận xử lý — tài liệu của tenant A."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    assert (await nap(factory, tenant_b, doc)).trang_thai == "BO_QUA"
    assert await trang_thai(factory, tenant_a, doc) == ("PENDING", None, 0, None)


# ── Lỗi vĩnh viễn và lỗi tạm thời ────────────────────────────────────────────


async def test_object_bien_mat_thi_failed_file_not_found(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "mat.pdf", "PDF", du_lieu=b"")
    ket_qua = await nap(factory, tenant_a, doc)
    assert (ket_qua.trang_thai, ket_qua.loi) == ("FAILED", "FILE_NOT_FOUND")


async def test_kho_s3_chet_thi_thu_lai_va_tai_lieu_quay_ve_pending(
    ha_tang, kho_s3, tenant_a, monkeypatch
):
    """Lỗi TẠM THỜI: tài liệu về PENDING (giữ attempt_count), nơi gọi thử lại sau.

    Nếu nuốt lỗi này thành FAILED thì một lần S3 chớp tắt làm hỏng vĩnh viễn một tệp tốt.
    (Ngày 4: ném ra để transaction huỷ. Ngày 5, ADR-0021: PROCESSING đã commit sớm nên phải tự
    trả về hàng đợi — hết lượt thì FAILED, xem ``test_nap_tai_lieu.py``.)
    """
    factory, cau_hinh = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")

    chet = object_storage.tao_client(cau_hinh.model_copy(update={"s3_endpoint": "127.0.0.1:1"}))
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: chet)
    ket_qua = await nap(factory, tenant_a, doc)

    assert (ket_qua.trang_thai, ket_qua.loi) == ("THU_LAI", "STORAGE_UNAVAILABLE")
    assert await trang_thai(factory, tenant_a, doc) == ("PENDING", None, 1, None)


@pytest.mark.parametrize("ten_tep,loai", [("faq-bao-hanh.html", "HTML"),
                                          ("chinh-sach-doi-tra.docx", "DOCX")])
async def test_moi_dinh_dang_deu_toi_ready(ha_tang, kho_s3, tenant_a, ten_tep, loai):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, ten_tep, loai)
    assert (await nap(factory, tenant_a, doc)).trang_thai == "READY"
