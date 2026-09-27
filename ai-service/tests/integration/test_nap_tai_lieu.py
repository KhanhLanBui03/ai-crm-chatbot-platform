"""UC019 (2/2) — nạp tới ``READY``, chống trùng, thử lại, mất quyền, bộ quét, tiến độ. Ngày 5.

Postgres (RLS, role ``ai_app``) và RustFS thật; ai-embed là ``MockEmbedClient`` (seed cố định —
ai-embed thật chưa dựng, ghi nợ đo lại ở Ngày 7). Lô nhúng 4 đoạn (``conftest.py``) để mọi tệp
mẫu đi qua nhiều lô.

Test Kafka thật (DLQ, khởi động lại worker giữa chừng) ở ``test_worker_kafka.py``.
"""

from uuid import uuid4

import httpx
import psycopg
import pytest
from sqlalchemy import text

from src.ai import service
from src.ai.db import session as db_session
from src.ai.db.repositories import document_repository
from src.ai.exceptions import EmbeddingUnavailableError
from src.ai.inference.clients import MockEmbedClient
from src.ai.integrations import object_storage
from src.api import deps
from src.api.main import create_app
from tests.integration.nap_chung import cac_doan, doc_mot, nap, tai_lieu_pending, trang_thai

DIM = 1024


class _EmbedHongLanThu(MockEmbedClient):
    """Mock chạy bình thường, riêng lần gọi thứ ``lan`` thì chạy ``viec`` (ném lỗi, tước quyền…)."""

    def __init__(self, lan: int, viec) -> None:
        super().__init__(DIM)
        self.lan, self.viec, self.da_goi = lan, viec, 0

    async def embed_batch(self, texts):
        self.da_goi += 1
        if self.da_goi == self.lan:
            await self.viec()
        return await super().embed_batch(texts)


# ── Cổng ra: tài liệu thật nằm trong knowledge_chunks có vector ─────────────


async def test_nap_tron_ven_ready_co_vector_va_chunk_count(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")

    ket_qua = await nap(factory, tenant_a, doc)

    assert ket_qua.trang_thai == "READY" and ket_qua.lan == 1
    doan = await cac_doan(factory, tenant_a, doc)
    assert len(doan) == ket_qua.so_doan > 4  # nhiều hơn một lô
    assert all(d[4] for d in doan), "đoạn nào cũng phải có vector"
    assert {d.embedding_model for d in doan} == {"mock-hash-1024"}
    assert all(d[6] for d in doan), "content_segmented (GENERATED) phải được tính"
    status, loi, lan, buoc, so, xong = await doc_mot(
        factory, tenant_a,
        "SELECT status, error_message, attempt_count, ingest_step, chunk_count,"
        " indexed_at IS NOT NULL AND indexed_at >= ingest_started_at"
        " FROM knowledge.knowledge_documents WHERE id = :id",
        id=doc,
    )
    assert (status, loi, lan, buoc, so, xong) == ("READY", None, 1, None, len(doan), True)


async def test_vector_luu_dung_gia_tri_mock_da_sinh(ha_tang, kho_s3, tenant_a):
    """Chuỗi hoá vector (``_vector_sang_chuoi``) không làm lệch giá trị: cosine với chính nó = 1."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "gio-mo-cua-chi-nhanh.txt", "TXT")
    await nap(factory, tenant_a, doc)
    noi_dung = (await cac_doan(factory, tenant_a, doc))[0].content
    vector = (await MockEmbedClient(DIM).embed_batch([noi_dung])).vectors[0]
    (khoang_cach,) = await doc_mot(
        factory, tenant_a,
        "SELECT embedding <=> CAST(:v AS vector) FROM knowledge.knowledge_chunks"
        " WHERE document_id = :id AND chunk_index = 0",
        id=doc, v="[" + ",".join(map(str, vector)) + "]",
    )
    assert khoang_cach < 1e-6


# ── Chống trùng sự kiện: ai.processed_events ─────────────────────────────────


async def test_su_kien_trung_thi_bo_qua_ma_khong_nap_lai(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    su_kien = service.SuKienNap("ingestion-cg", 900_001)

    assert (await nap(factory, tenant_a, doc, su_kien=su_kien)).trang_thai == "READY"
    assert (await nap(factory, tenant_a, doc, su_kien=su_kien)).trang_thai == "TRUNG"
    assert (await trang_thai(factory, tenant_a, doc))[2] == 1  # không nhận xử lý lần hai


async def test_ghi_nhan_su_kien_cung_transaction_voi_buoc_nhan_viec(ha_tang, tenant_a):
    """Tài liệu không nhận được (không tồn tại / không thuộc tenant) thì sự kiện VẪN được ghi nhận
    là đã xử lý — việc của nó (đưa tài liệu vào tay worker) đã có kết cục."""
    factory, _ = ha_tang
    su_kien = service.SuKienNap("ingestion-cg", 900_002)
    assert (await nap(factory, tenant_a, uuid4(), su_kien=su_kien)).trang_thai == "BO_QUA"
    assert (await nap(factory, tenant_a, uuid4(), su_kien=su_kien)).trang_thai == "TRUNG"


async def test_processed_events_co_rls(ha_tang, tenant_a, tenant_b):
    factory, _ = ha_tang
    su_kien = service.SuKienNap("ingestion-cg", 900_003)
    await nap(factory, tenant_a, uuid4(), su_kien=su_kien)
    (so_a,) = await doc_mot(factory, tenant_a,
                            "SELECT count(*) FROM ai.processed_events WHERE event_id = 900003")
    (so_b,) = await doc_mot(factory, tenant_b,
                            "SELECT count(*) FROM ai.processed_events WHERE event_id = 900003")
    assert (so_a, so_b) == (1, 0)


# ── Lỗi tạm thời: thử lại tới trần rồi FAILED ────────────────────────────────


async def test_kho_s3_chet_ba_luot_thi_failed_het_luot(ha_tang, kho_s3, tenant_a, monkeypatch):
    factory, cau_hinh = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    chet = object_storage.tao_client(cau_hinh.model_copy(update={"s3_endpoint": "127.0.0.1:1"}))
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: chet)

    assert [(await nap(factory, tenant_a, doc)).trang_thai for _ in range(3)] == [
        "THU_LAI", "THU_LAI", "FAILED",
    ]
    status, loi, lan, buoc = await trang_thai(factory, tenant_a, doc)
    assert (status, lan, buoc) == ("FAILED", 3, "EXTRACTING")
    assert loi.startswith("INGEST_RETRY_EXHAUSTED: STORAGE_UNAVAILABLE: ")
    assert "127.0.0.1" not in loi  # địa chỉ nội bộ chỉ vào log, không lên SCR033


async def test_ai_embed_chet_giua_chung_thi_don_doan_do_dang(ha_tang, kho_s3, tenant_a):
    """Lô 1 đã vào kho, lô 2 hỏng: lượt thử lại phải bắt đầu từ trang trắng — còn sót đoạn cũ thì
    lượt sau đụng ``uq_chunk_index`` hoặc để lại đoạn trùng."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")

    async def ai_embed_chet():
        raise EmbeddingUnavailableError("ai-embed trả 503")

    ket_qua = await nap(factory, tenant_a, doc, embed=_EmbedHongLanThu(2, ai_embed_chet))
    assert (ket_qua.trang_thai, ket_qua.loi) == ("THU_LAI", "EMBEDDING_UNAVAILABLE")
    assert await cac_doan(factory, tenant_a, doc) == []

    ket_qua = await nap(factory, tenant_a, doc)
    assert (ket_qua.trang_thai, ket_qua.lan) == ("READY", 2)
    doan = await cac_doan(factory, tenant_a, doc)
    assert [d.chunk_index for d in doan] == list(range(ket_qua.so_doan))


# ── Thẻ sở hữu: lượt bị bộ quét tước quyền thì dừng, không ghi đè ────────────


async def test_mat_quyen_giua_chung_thi_dung_khong_ghi_them(
    ha_tang, kho_s3, tenant_a, doi_cau_hinh
):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")

    async def bo_quet_chen_ngang():
        # Tiến trình "treo" giữa lô 1 và lô 2 đủ lâu để bị coi là chết (quá hạn = 0 s).
        doi_cau_hinh(kb_job_ket_sau_s=0.0)
        tra_ve = await service.quet_job_ket(factory=factory)
        doi_cau_hinh(kb_job_ket_sau_s=300.0)
        assert doc in {j.document_id for j in tra_ve}

    ket_qua = await nap(factory, tenant_a, doc, embed=_EmbedHongLanThu(2, bo_quet_chen_ngang))

    assert (ket_qua.trang_thai, ket_qua.lan) == ("MAT_QUYEN", 1)
    # Lượt cũ không được ghi lô 2 sau khi mất quyền, cũng không được đổi trạng thái.
    assert await trang_thai(factory, tenant_a, doc) == ("PENDING", None, 1, None)
    assert await cac_doan(factory, tenant_a, doc) == []

    ket_qua = await nap(factory, tenant_a, doc)
    assert (ket_qua.trang_thai, ket_qua.lan) == ("READY", 2)


async def test_luot_cu_tinh_lai_khong_ghi_de_luot_moi_da_nhan_lai(
    ha_tang, kho_s3, tenant_a, doi_cau_hinh
):
    """Ca khó nhất: bộ quét trả về PENDING VÀ lượt mới đã nhận lại (status lại là PROCESSING) trước
    khi lượt cũ tỉnh dậy. Chỉ ``status = 'PROCESSING'`` thì lượt cũ vượt qua được — chính
    ``attempt_count = :lan`` mới chặn nó."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")

    async def luot_moi_nhan_lai():
        doi_cau_hinh(kb_job_ket_sau_s=0.0)
        await service.quet_job_ket(factory=factory)
        doi_cau_hinh(kb_job_ket_sau_s=300.0)
        assert await _nhan_roi_chet(factory, tenant_a, doc) == 2

    ket_qua = await nap(factory, tenant_a, doc, embed=_EmbedHongLanThu(2, luot_moi_nhan_lai))

    assert (ket_qua.trang_thai, ket_qua.lan) == ("MAT_QUYEN", 1)
    assert await trang_thai(factory, tenant_a, doc) == ("PROCESSING", None, 2, "EXTRACTING")
    assert await cac_doan(factory, tenant_a, doc) == []  # lô 2 của lượt cũ không lọt vào kho


# ── Bộ quét job kẹt ──────────────────────────────────────────────────────────


async def _nhan_roi_chet(factory, tenant, doc) -> int:
    """Nhận việc rồi "chết": PROCESSING đã commit, không ai làm tiếp."""
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return (await document_repository.nhan_xu_ly(phien, doc)).lan


async def test_bo_quet_tra_job_ket_ve_hang_doi_roi_nap_lai_duoc(
    ha_tang, kho_s3, tenant_a, doi_cau_hinh
):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    await _nhan_roi_chet(factory, tenant_a, doc)

    doi_cau_hinh(kb_job_ket_sau_s=300.0)
    assert doc not in {j.document_id for j in await service.quet_job_ket(factory=factory)}

    doi_cau_hinh(kb_job_ket_sau_s=0.0)
    tra_ve = await service.quet_job_ket(factory=factory)
    assert service.JobCanNapLai(str(tenant_a), doc) in tra_ve
    assert await trang_thai(factory, tenant_a, doc) == ("PENDING", None, 1, None)

    doi_cau_hinh(kb_job_ket_sau_s=300.0)
    assert (await nap(factory, tenant_a, doc)).trang_thai == "READY"


async def test_bo_quet_het_luot_thi_failed_ingest_stalled(ha_tang, kho_s3, tenant_a, doi_cau_hinh):
    """Tệp làm worker chết thì làm chết mọi lượt — không có trần là vòng khởi động lại vô hạn."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    doi_cau_hinh(kb_job_ket_sau_s=0.0)

    for _ in range(3):
        await _nhan_roi_chet(factory, tenant_a, doc)
        await service.quet_job_ket(factory=factory)

    status, loi, lan, buoc = await trang_thai(factory, tenant_a, doc)
    assert (status, lan, buoc) == ("FAILED", 3, "EXTRACTING")
    assert loi.startswith("INGEST_STALLED: ")


async def test_bo_quet_bo_qua_pending_chua_tung_co_su_kien(ha_tang, kho_s3, tenant_a, doi_cau_hinh):
    """PENDING + attempt_count = 0: sự kiện còn trên đường, hoặc java-core đã rollback lượt tải.
    Tự nạp là nạp một tài liệu không được tính hạn mức (hợp đồng UC018 mục 4)."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    doi_cau_hinh(kb_job_ket_sau_s=0.0)
    assert doc not in {j.document_id for j in await service.quet_job_ket(factory=factory)}


async def test_bo_quet_nhat_lai_pending_da_tra_ve_ma_worker_chet(
    ha_tang, kho_s3, tenant_a, doi_cau_hinh
):
    """THU_LAI đưa tài liệu về PENDING (attempt_count = 1); worker chết trong lúc chờ thử lại thì
    không còn sự kiện nào gọi lại nó — bộ quét phải nhặt."""
    factory, cau_hinh = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")

    async def chet():
        raise EmbeddingUnavailableError("503")

    assert (await nap(factory, tenant_a, doc, embed=_EmbedHongLanThu(1, chet))).trang_thai == (
        "THU_LAI"
    )
    doi_cau_hinh(kb_job_ket_sau_s=0.0)
    assert service.JobCanNapLai(str(tenant_a), doc) in await service.quet_job_ket(factory=factory)


# ── Hàm SECURITY DEFINER: lỗ hẹp nhất có thể ─────────────────────────────────


async def test_phien_he_thong_khong_doc_duoc_bang_nao(ha_tang):
    """Phiên không gắn tenant chỉ gọi được hàm quét; chạm bảng thật là 42501 ngay (fail-closed)."""
    factory, _ = ha_tang
    with pytest.raises(Exception, match="app.tenant_id"):
        async with db_session.get_system_session(factory) as phien:
            await phien.execute(text("SELECT count(*) FROM knowledge.knowledge_documents"))


def test_ham_quet_chi_ai_app_goi_duoc_va_ghim_search_path(pg_dsn_ai_app):
    with psycopg.connect(pg_dsn_ai_app) as conn:
        dinh_nghia, cau_hinh, crm_app, ai_app = conn.execute(
            """
            SELECT p.prosecdef, p.proconfig,
                   has_function_privilege('crm_app', p.oid, 'EXECUTE'),
                   has_function_privilege('ai_app', p.oid, 'EXECUTE')
              FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'knowledge' AND p.proname = 'tim_job_ket'
            """
        ).fetchone()
        so_cot = len(conn.execute(
            "SELECT * FROM knowledge.tim_job_ket(interval '0', 1)"
        ).description)
    assert dinh_nghia is True
    assert cau_hinh == ["search_path=pg_catalog, pg_temp"]
    assert (crm_app, ai_app) == (False, True)
    assert so_cot == 4  # tenant_id, document_id, status, attempt_count — không nội dung


# ── Tiến độ 6 bước — GET /v1/ai/kb/ingestion-jobs/{job_id} ───────────────────


@pytest.fixture
async def client(ha_tang):
    factory, _ = ha_tang

    async def _phien_test(tenant_id: deps.TenantIdDep):
        async with db_session.get_tenant_session(tenant_id, factory=factory) as phien:
            yield phien

    app = create_app()
    app.dependency_overrides[deps.get_session] = _phien_test
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _tien_do(client, tenant, doc) -> httpx.Response:
    return await client.get(
        f"/v1/ai/kb/ingestion-jobs/{doc}", headers={"X-Tenant-Id": str(tenant)}
    )


async def test_tien_do_queued_roi_done(client, ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")

    truoc = (await _tien_do(client, tenant_a, doc)).json()
    assert (truoc["state"], truoc["attempt"], truoc["chunks_total"]) == ("QUEUED", 0, None)
    assert [s["state"] for s in truoc["steps"]] == ["RUNNING"] + ["PENDING"] * 5

    await nap(factory, tenant_a, doc)
    sau = (await _tien_do(client, tenant_a, doc)).json()
    assert (sau["state"], sau["percent"], sau["attempt"]) == ("DONE", 100.0, 1)
    assert sau["chunks_created"] == sau["chunks_total"] > 0
    assert [s["step"] for s in sau["steps"]] == [
        "QUEUED", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING", "DONE",
    ]
    assert {s["state"] for s in sau["steps"]} == {"DONE"}
    assert sau["duration_ms"] >= 0 and sau["finished_at"] is not None


async def test_tien_do_giua_chung_embedding(client, ha_tang, kho_s3, tenant_a):
    """Đọc tiến độ TRONG LÚC đang nhúng — thứ phương án 2 của ADR-0021 mua được."""
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "chinh-sach-bao-hanh.pdf", "PDF")
    anh_chup: dict = {}

    async def chup():
        anh_chup.update((await _tien_do(client, tenant_a, doc)).json())

    await nap(factory, tenant_a, doc, embed=_EmbedHongLanThu(2, chup))

    assert anh_chup["state"] == "EMBEDDING" and anh_chup["status"] == "PROCESSING"
    assert anh_chup["chunks_created"] == 4  # lô 1 đã vào kho, lô 2 đang nhúng
    assert anh_chup["chunks_total"] > 4
    assert 0 < anh_chup["percent"] < 100
    assert [s["state"] for s in anh_chup["steps"]] == [
        "DONE", "DONE", "DONE", "RUNNING", "PENDING", "PENDING",
    ]


async def test_tien_do_failed_co_ma_loi_va_buoc_hong(client, ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "ban-scan-bao-hanh.pdf", "PDF")
    await nap(factory, tenant_a, doc)

    td = (await _tien_do(client, tenant_a, doc)).json()
    assert (td["state"], td["error_code"]) == ("FAILED", "PARSE_NO_TEXT_EXTRACTED")
    assert "OCR" in td["error_message"] and not td["error_message"].startswith("PARSE_")
    assert [s["state"] for s in td["steps"]] == ["DONE", "FAILED"] + ["SKIPPED"] * 4


async def test_tien_do_cua_tenant_khac_la_404(client, ha_tang, kho_s3, tenant_a, tenant_b):
    factory, _ = ha_tang
    doc = await tai_lieu_pending(factory, kho_s3, tenant_a, "faq-thanh-toan.txt", "TXT")
    phan_hoi = await _tien_do(client, tenant_b, doc)
    assert (phan_hoi.status_code, phan_hoi.json()["code"]) == (404, "DOCUMENT_NOT_FOUND")
    assert (await _tien_do(client, tenant_a, doc)).status_code == 200
