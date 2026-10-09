"""UC020 — quản lý kho tri thức: nạp lại bằng bản bóng, gỡ, tìm không dấu, xem đoạn. Ngày 11.

Postgres (RLS, role ``ai_app``) và RustFS thật; nhúng bằng ``MockEmbedClient`` — phép thử ở đây
là về TRẠNG THÁI kho, không về chất lượng vector.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Nạp lại có khoảnh khắc nào kho trống không? →
  ``test_nap_lai_khong_co_khoanh_khac_nao_kho_trong`` (hỏi bằng đúng hàm truy hồi lai của
  production ở MỌI lô nhúng + một tác vụ hỏi liên tục suốt lượt).
- Nạp lại hỏng thì sao? → ``test_ban_bong_hong_thi_ban_cu_van_phuc_vu``.
- Vì sao xoá đoạn trước rồi mới ARCHIVED? → ``test_go_hong_giua_chung_thi_giu_nguyen_trang_thai``.
- "bao gia" có khớp "báo giá" không? → ``test_tim_khong_dau_khong_phan_biet_hoa_thuong``.
"""

import asyncio
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.ai import service
from src.ai.db import session as db_session
from src.ai.db.repositories import chunk_repository, document_repository
from src.ai.exceptions import EmbeddingRejectedError
from src.ai.inference.clients import MockEmbedClient
from src.ai.rag.retrieve.hybrid import tim_kiem_lai
from tests.conftest import AI_PASSWORD, AI_USER, OWNER_PASSWORD, OWNER_USER
from tests.integration.nap_chung import cac_doan, nap, tai_lieu_pending, trang_thai

DIM = 1024
TEP = "faq-thanh-toan.txt"


async def _tai_lieu_ready(factory, kho_s3, tenant: UUID) -> UUID:
    doc = await tai_lieu_pending(factory, kho_s3, tenant, TEP, "TXT")
    assert (await nap(factory, tenant, doc)).trang_thai == "READY"
    return doc


async def _tao_ban_bong(factory, tenant: UUID, doc: UUID) -> UUID:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        cu = await document_repository.lay_tai_lieu(phien, doc, khoa=True)
        moi, _ = await document_repository.tao_ban_bong(phien, cu)
    return moi


async def _truy_hoi_thay(factory, tenant: UUID, cac_doc: set[UUID]) -> int:
    """Số đoạn của ``cac_doc`` mà ĐÚNG hàm truy hồi lai production trả về (k lớn, vector mock)."""
    nhung = await MockEmbedClient(DIM).embed_batch(["thanh toán chuyển khoản"])
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        ket_qua = await tim_kiem_lai(
            phien,
            vector=nhung.vectors[0],
            tsquery=None,
            embedding_model=nhung.model_id,
            embedding_version=nhung.model_version,
            k=200,
            ung_vien=200,
        )
    return sum(d.document_id in cac_doc for d in ket_qua)


class _NhungCoTham(MockEmbedClient):
    """Mock nhúng; trước MỖI lô chạy ``tham`` (một phép hỏi kho) — giữa lúc bản bóng đang nạp."""

    def __init__(self, tham) -> None:
        super().__init__(DIM)
        self.tham = tham
        self.so_lo = 0

    async def embed_batch(self, texts):
        self.so_lo += 1
        await self.tham()
        return await super().embed_batch(texts)


# ── Nạp lại: bản bóng, đổi bản trong một transaction ────────────────────────


async def test_nap_lai_khong_co_khoanh_khac_nao_kho_trong(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    cu = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    so_doan_cu = len(await cac_doan(factory, tenant_a, cu))
    moi = await _tao_ban_bong(factory, tenant_a, cu)
    hai_ban = {cu, moi}

    quan_sat: list[int] = []

    async def hoi_kho():
        quan_sat.append(await _truy_hoi_thay(factory, tenant_a, hai_ban))

    dung = asyncio.Event()

    async def hoi_lien_tuc():
        while not dung.is_set():
            await hoi_kho()
            await asyncio.sleep(0)

    nen = asyncio.create_task(hoi_lien_tuc())
    nhung = _NhungCoTham(hoi_kho)
    try:
        ket_qua = await nap(factory, tenant_a, moi, embed=nhung)
    finally:
        dung.set()
        await nen
    await hoi_kho()  # sau khi đổi bản

    assert ket_qua.trang_thai == "READY" and nhung.so_lo >= 2
    assert len(quan_sat) > nhung.so_lo  # có quan sát xen giữa các chặng, không chỉ ở mỗi lô
    assert min(quan_sat) > 0  # 0 giây kho trống
    # Không lần hỏi nào thấy CẢ hai bản cùng lúc: số đoạn thấy được luôn là của đúng một bản.
    so_doan_moi = len(await cac_doan(factory, tenant_a, moi))
    assert set(quan_sat) <= {so_doan_cu, so_doan_moi}
    assert (await trang_thai(factory, tenant_a, cu))[0] == "ARCHIVED"
    assert await cac_doan(factory, tenant_a, cu) == []  # đoạn bản cũ đã xoá
    assert (await trang_thai(factory, tenant_a, moi))[0] == "READY"


async def test_ban_bong_hong_thi_ban_cu_van_phuc_vu(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    cu = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    moi = await _tao_ban_bong(factory, tenant_a, cu)

    class _NhungTuChoi(MockEmbedClient):
        async def embed_batch(self, texts):
            raise EmbeddingRejectedError("ai-embed trả sai số chiều")

    ket_qua = await nap(factory, tenant_a, moi, embed=_NhungTuChoi(DIM))
    assert ket_qua.trang_thai == "FAILED"
    assert (await trang_thai(factory, tenant_a, cu))[0] == "READY"
    assert await _truy_hoi_thay(factory, tenant_a, {cu}) > 0


async def test_hai_luot_nap_lai_chong_nhau_bi_chan_o_csdl(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    cu = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    await _tao_ban_bong(factory, tenant_a, cu)
    with pytest.raises(IntegrityError, match="uq_doc_mot_luot_nap_lai"):
        await _tao_ban_bong(factory, tenant_a, cu)


async def test_ban_bong_mang_version_ke_tiep_va_cung_tep(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    cu = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    moi = await _tao_ban_bong(factory, tenant_a, cu)
    async with db_session.get_tenant_session(str(tenant_a), factory=factory) as phien:
        a = (await phien.execute(text(
            "SELECT title, version, file_path, replaces_document_id, status"
            " FROM knowledge.knowledge_documents WHERE id = ANY(:ids) ORDER BY version"
        ), {"ids": [cu, moi]})).all()
        ban_cu = await document_repository.lay_tai_lieu(phien, cu)
    assert a[0].title == a[1].title and a[0].file_path == a[1].file_path
    assert (a[1].version, a[1].replaces_document_id, a[1].status) == (
        a[0].version + 1, cu, "PENDING"
    )
    assert ban_cu.reindex_document_id == moi  # bản cũ biết ai đang nạp lại nó


async def test_bo_quet_nhat_ban_bong_ngay_khong_cho_qua_han(
    ha_tang, kho_s3, tenant_a, doi_cau_hinh
):
    factory, _ = ha_tang
    cu = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    moi = await _tao_ban_bong(factory, tenant_a, cu)
    doi_cau_hinh(kb_job_ket_sau_s=300.0)
    tra_ve = await service.quet_job_ket(factory=factory)
    assert service.JobCanNapLai(str(tenant_a), moi) in tra_ve
    # Tài liệu PENDING thường (chưa có sự kiện) vẫn KHÔNG bị bộ quét tự nạp (V211, hợp đồng UC018).
    thuong = await tai_lieu_pending(factory, kho_s3, tenant_a, TEP, "TXT")
    assert thuong not in {j.document_id for j in await service.quet_job_ket(factory=factory)}


# ── Gỡ khỏi chỉ mục ──────────────────────────────────────────────────────────


async def test_go_xoa_doan_roi_moi_archived(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    async with db_session.get_tenant_session(str(tenant_a), factory=factory) as phien:
        await document_repository.lay_tai_lieu(phien, doc, khoa=True)
        so_xoa = await document_repository.xoa_khoi_chi_muc(phien, doc)
    assert so_xoa > 0
    assert (await trang_thai(factory, tenant_a, doc))[0] == "ARCHIVED"
    assert await cac_doan(factory, tenant_a, doc) == []
    assert await _truy_hoi_thay(factory, tenant_a, {doc}) == 0


async def test_go_hong_giua_chung_thi_giu_nguyen_trang_thai(ha_tang, kho_s3, tenant_a):
    """Đặc tả UC020 luồng phụ 7.2: không bao giờ có tài liệu ARCHIVED mà vector còn trong chỉ mục,
    cũng không có đoạn bị xoá mà tài liệu vẫn READY — cả hai câu cùng một transaction."""
    factory, _ = ha_tang
    doc = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    so_doan = len(await cac_doan(factory, tenant_a, doc))
    with pytest.raises(RuntimeError, match="giả lập"):
        async with db_session.get_tenant_session(str(tenant_a), factory=factory) as phien:
            await document_repository.lay_tai_lieu(phien, doc, khoa=True)
            await document_repository.xoa_khoi_chi_muc(phien, doc)
            raise RuntimeError("giả lập CSDL rớt kết nối trước khi commit")
    assert (await trang_thai(factory, tenant_a, doc))[0] == "READY"
    assert len(await cac_doan(factory, tenant_a, doc)) == so_doan


# ── Tìm, xem đoạn ────────────────────────────────────────────────────────────


async def _them(factory, tenant: UUID, title: str, mo_ta: str | None = None, ten_tep="t.txt"):
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return await document_repository.them_tai_lieu_pending(
            phien, title=title, description=mo_ta, language="vi", source_type="TXT",
            file_name=ten_tep, file_path=f"s3://kb/{tenant}/{uuid4()}/{ten_tep}",
            mime_type="text/plain", file_size_bytes=10, version=1, uploaded_by=None,
        )


async def _tim(factory, tenant: UUID, tu_khoa=None, status=None):
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        cac, tong = await document_repository.danh_sach(
            phien, tu_khoa=tu_khoa, status=status, source_type=None, gioi_han=20, bo_qua=0
        )
    return [t.title for t in cac], tong


async def test_tim_khong_dau_khong_phan_biet_hoa_thuong(ha_tang):
    factory, _ = ha_tang
    t = uuid4()
    await _them(factory, t, "Báo giá máy lạnh 2026")
    await _them(factory, t, "Chính sách đổi trả", mo_ta="Áp dụng cho BÁO GIÁ khuyến mãi")
    await _them(factory, t, "Hướng dẫn lắp đặt", ten_tep="bao-gia-cu.pdf")
    await _them(factory, t, "Giờ mở cửa")
    ten, tong = await _tim(factory, t, "bao gia")
    assert tong == 2 and set(ten) == {"Báo giá máy lạnh 2026", "Chính sách đổi trả"}
    # "bao-gia" trong tên tệp: dấu gạch là ký tự thường, không phải dấu cách
    assert (await _tim(factory, t, "bao-gia"))[0] == ["Hướng dẫn lắp đặt"]
    assert (await _tim(factory, t, "MÁY LẠNH"))[0] == ["Báo giá máy lạnh 2026"]
    assert (await _tim(factory, t))[1] == 4


async def test_tu_khoa_chua_ky_tu_dai_dien_la_ky_tu_thuong(ha_tang):
    factory, _ = ha_tang
    t = uuid4()
    await _them(factory, t, "Giảm 50% phí lắp đặt")
    await _them(factory, t, "Giảm 500 nghìn")
    assert (await _tim(factory, t, "50%"))[0] == ["Giảm 50% phí lắp đặt"]
    assert (await _tim(factory, t, "_"))[1] == 0  # "_" không khớp mọi ký tự


async def test_danh_sach_an_archived_tru_khi_loc(ha_tang, kho_s3):
    factory, _ = ha_tang
    t = uuid4()
    doc = await _tai_lieu_ready(factory, kho_s3, t)
    async with db_session.get_tenant_session(str(t), factory=factory) as phien:
        await document_repository.lay_tai_lieu(phien, doc, khoa=True)
        await document_repository.xoa_khoi_chi_muc(phien, doc)
    assert (await _tim(factory, t))[1] == 0
    assert (await _tim(factory, t, status="ARCHIVED"))[1] == 1


def test_bieu_thuc_tim_khop_chi_muc_trigram(pg_dsn_ai_app):
    """Biểu thức của câu tìm phải trùng TỪNG KÝ TỰ biểu thức của ix_doc_tim_kiem (V213) — lệch một
    ký tự là Postgres không dùng được chỉ mục. EXPLAIN bằng role chủ bảng: dưới RLS, với vài chục
    tài liệu mỗi tenant, planner chọn chỉ mục theo tenant (đúng ở quy mô này); điều cần chứng minh
    là chỉ mục trigram DÙNG ĐƯỢC khi kho của tenant lớn lên."""
    dsn = pg_dsn_ai_app.replace(f"{AI_USER}:{AI_PASSWORD}@", f"{OWNER_USER}:{OWNER_PASSWORD}@")
    with psycopg.connect(dsn) as conn:
        conn.execute("SET enable_seqscan = off")
        ke_hoach = conn.execute(
            "EXPLAIN SELECT 1 FROM knowledge.knowledge_documents d WHERE "
            + document_repository._BIEU_THUC_TIM
            + " LIKE '%%' || lower(knowledge.f_unaccent(%s)) || '%%' ESCAPE '\\'",
            ("bao gia",),
        ).fetchall()
    assert "ix_doc_tim_kiem" in " ".join(d[0] for d in ke_hoach)


async def test_xem_doan_khong_tra_vector(ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    doc = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    async with db_session.get_tenant_session(str(tenant_a), factory=factory) as phien:
        cac, tong = await chunk_repository.danh_sach_doan(phien, doc, 2, 0)
    assert tong == len(await cac_doan(factory, tenant_a, doc)) and len(cac) == min(2, tong)
    assert [d.chunk_index for d in cac] == list(range(len(cac)))
    assert all(d.co_vector and d.embedding_model == "mock-hash-1024" for d in cac)
    assert "embedding" not in chunk_repository.DoanXem.__slots__


async def test_tai_lieu_tenant_khac_khong_thay(ha_tang, kho_s3, tenant_a, tenant_b):
    factory, _ = ha_tang
    doc = await _tai_lieu_ready(factory, kho_s3, tenant_a)
    async with db_session.get_tenant_session(str(tenant_b), factory=factory) as phien:
        assert await document_repository.lay_tai_lieu(phien, doc) is None
        assert (await chunk_repository.danh_sach_doan(phien, doc, 10, 0))[1] == 0
