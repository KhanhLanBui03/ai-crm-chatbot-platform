"""UC019 (1/2) — ``service.phan_tich_tai_lieu`` trên Postgres (RLS) và RustFS (S3) thật.

Cổng ra Ngày 4: PDF scan chuyển ``FAILED`` kèm ``error_message`` — mã lỗi thứ 5 của UC018
(``PARSE_NO_TEXT_EXTRACTED``), chỉ đo được khi có parser.

Luồng mỗi test: đưa tệp lên S3 dưới key của tenant → ghi dòng ``PENDING`` như UC018 → gọi
facade trong một phiên MỚI (như worker Ngày 5 sẽ gọi) → đọc lại trạng thái.
"""

import io
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from src.ai import service
from src.ai.config import Settings
from src.ai.db import session as db_session
from src.ai.db.repositories import document_repository
from src.ai.exceptions import StorageUnavailableError
from src.ai.integrations import object_storage
from tests.conftest import S3_ACCESS_KEY, S3_BUCKET, S3_SECRET_KEY

MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"


@pytest.fixture
async def ha_tang(pg_dsn_ai_app, kho_s3_endpoint, monkeypatch):
    """Nối facade vào Postgres và RustFS của test. Trả về (factory phiên CSDL, cấu hình)."""
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    factory = db_session.tao_session_factory(engine)
    cau_hinh = Settings(
        s3_endpoint=kho_s3_endpoint,
        s3_bucket=S3_BUCKET,
        s3_access_key=S3_ACCESS_KEY,
        s3_secret_key=S3_SECRET_KEY,
    )
    monkeypatch.setattr(service, "get_settings", lambda: cau_hinh)
    client_s3 = object_storage.tao_client(cau_hinh)
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: client_s3)
    yield factory, cau_hinh
    await engine.dispose()


async def _tai_lieu_pending(factory, kho_s3, tenant: UUID, ten_tep: str, source_type: str,
                            du_lieu: bytes | None = None) -> UUID:
    """Làm đúng phần việc của UC018: object dưới key của tenant + dòng PENDING."""
    key = f"{tenant}/{uuid4()}/{ten_tep}"
    if du_lieu is None:
        du_lieu = (MAU / ten_tep).read_bytes()
    if du_lieu:  # b"" = cố ý KHÔNG đưa lên S3
        kho_s3.put_object(S3_BUCKET, key, io.BytesIO(du_lieu), len(du_lieu))
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return await document_repository.them_tai_lieu_pending(
            phien,
            title=f"{ten_tep} [{uuid4().hex[:8]}]",
            description=None,
            language="vi",
            source_type=source_type,
            file_name=ten_tep,
            file_path=f"s3://{S3_BUCKET}/{key}",
            mime_type="application/octet-stream",
            file_size_bytes=len(du_lieu),
            version=1,
            uploaded_by=None,
        )


async def _phan_tich(factory, tenant: UUID, doc: UUID) -> service.KetQuaPhanTich:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return await service.phan_tich_tai_lieu(phien, str(tenant), doc)


async def _trang_thai(factory, tenant: UUID, doc: UUID) -> tuple[str, str | None]:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        dong = await phien.execute(
            text("SELECT status, error_message FROM knowledge.knowledge_documents WHERE id = :id"),
            {"id": doc},
        )
        return tuple(dong.one())


# ── Cổng ra Ngày 4 ───────────────────────────────────────────────────────────


async def test_pdf_scan_chuyen_failed_kem_parse_no_text_extracted(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await _tai_lieu_pending(factory, kho_s3, tenant_a, "ban-scan-bao-hanh.pdf", "PDF")

    ket_qua = await _phan_tich(factory, tenant_a, doc)

    assert (ket_qua.trang_thai, ket_qua.loi) == ("FAILED", "PARSE_NO_TEXT_EXTRACTED")
    trang_thai, loi = await _trang_thai(factory, tenant_a, doc)
    assert trang_thai == "FAILED"
    assert loi.startswith("PARSE_NO_TEXT_EXTRACTED: ")
    assert "OCR" in loi  # câu cho người dùng biết cách sửa


# ── Luồng tốt ────────────────────────────────────────────────────────────────


async def test_pdf_tot_ra_doan_co_heading_va_trang(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await _tai_lieu_pending(factory, kho_s3, tenant_a, "bang-gia-2026.pdf", "PDF")

    ket_qua = await _phan_tich(factory, tenant_a, doc)

    assert ket_qua.trang_thai == "PROCESSING"
    assert await _trang_thai(factory, tenant_a, doc) == ("PROCESSING", None)
    may_lanh = [d for d in ket_qua.doan if d.heading == "Bảng giá sản phẩm 2026 > 3. Máy lạnh"]
    assert may_lanh and may_lanh[0].page_number == 2
    assert "NH-ML09 |" in may_lanh[0].content
    assert [d.chunk_index for d in ket_qua.doan] == list(range(len(ket_qua.doan)))


async def test_noi_dung_da_chuan_hoa(ha_tang, kho_s3, tenant_a):
    """Tệp "bẩn có chủ đích" (NFD + U+200B + hoà/hòa): đoạn ra phải sạch như câu hỏi sẽ sạch."""
    factory, _ = ha_tang
    doc = await _tai_lieu_pending(
        factory, kho_s3, tenant_a, "huong-dan-bao-quan-noi-chien.txt", "TXT"
    )
    ket_qua = await _phan_tich(factory, tenant_a, doc)
    tat_ca = "\n".join(d.content + (d.heading or "") for d in ket_qua.doan)
    assert "​" not in tat_ca and "thuỷ" not in tat_ca


# ── Chống nhận trùng và cô lập tenant ────────────────────────────────────────


async def test_goi_lan_hai_thi_bo_qua(ha_tang, kho_s3, tenant_a):
    """Kafka giao ít nhất một lần: sự kiện trùng tới sau không được phân tích lại."""
    factory, _ = ha_tang
    doc = await _tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    assert (await _phan_tich(factory, tenant_a, doc)).trang_thai == "PROCESSING"
    assert (await _phan_tich(factory, tenant_a, doc)).trang_thai == "BO_QUA"


async def test_tai_lieu_cua_tenant_khac_thi_bo_qua(ha_tang, kho_s3, tenant_a, tenant_b):
    """RLS: phiên tenant B không nhìn thấy — càng không nhận xử lý — tài liệu của tenant A."""
    factory, _ = ha_tang
    doc = await _tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    assert (await _phan_tich(factory, tenant_b, doc)).trang_thai == "BO_QUA"
    assert await _trang_thai(factory, tenant_a, doc) == ("PENDING", None)


# ── Lỗi vĩnh viễn và lỗi tạm thời ────────────────────────────────────────────


async def test_object_bien_mat_thi_failed_file_not_found(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await _tai_lieu_pending(factory, kho_s3, tenant_a, "mat.pdf", "PDF", du_lieu=b"")
    ket_qua = await _phan_tich(factory, tenant_a, doc)
    assert (ket_qua.trang_thai, ket_qua.loi) == ("FAILED", "FILE_NOT_FOUND")


async def test_kho_s3_chet_thi_nem_va_tai_lieu_quay_ve_pending(
    ha_tang, kho_s3, tenant_a, monkeypatch
):
    """Lỗi TẠM THỜI: ném ra để transaction huỷ — tài liệu về PENDING, worker nhận lại sau.

    Nếu nuốt lỗi này thành FAILED thì một lần S3 chớp tắt làm hỏng vĩnh viễn một tệp tốt.
    """
    factory, cau_hinh = ha_tang
    doc = await _tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")

    chet = object_storage.tao_client(cau_hinh.model_copy(update={"s3_endpoint": "127.0.0.1:1"}))
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: chet)
    with pytest.raises(StorageUnavailableError):
        await _phan_tich(factory, tenant_a, doc)

    assert await _trang_thai(factory, tenant_a, doc) == ("PENDING", None)
