"""Truy hồi lai trên Postgres THẬT — ``src/ai/rag/retrieve/hybrid.py``.

Mỗi test chạy trong MỘT transaction rồi rollback: không để lại dòng nào cho test khác. Vector
dựng tay trên vài trục của không gian 1024 chiều, nên thứ hạng làn vector biết trước chính xác.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Hai tenant có tài liệu GIỐNG HỆT nhau thì sao? → ``test_chi_tra_doan_cua_tenant_dang_gan``
- RLS cấu hình sai thì còn gì chặn? → ``test_hang_rao_thu_hai_khi_rls_bi_bo_qua``
- Đoạn của job đang nạp có lọt vào câu trả lời không? → ``test_bo_doan_cua_tai_lieu_chua_ready``
- Đổi model nhúng giữa chừng thì sao? → ``test_bo_doan_khac_the_he_nhung``
- Vì sao RRF mà không cộng điểm? → ``test_dong_thuan_hai_lan_thang_hang_nhat_mot_lan``
- Có chắc là dùng HNSW không? → ``test_lan_vector_dung_chi_muc_hnsw``
- ``iterative_scan`` để làm gì? → ``test_quet_lap_cuu_tenant_nho_trong_kho_dong``
"""

import math
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.ai.db import session as db_session
from src.ai.db.repositories.chunk_repository import vector_sang_chuoi
from src.ai.rag.retrieve import hybrid
from src.ai.rag.retrieve.hybrid import RRF_K, tim_kiem_lai
from src.ai.rag.tsquery import build_tsquery
from tests.conftest import AI_PASSWORD, AI_USER, OWNER_PASSWORD, OWNER_USER, REPO_ROOT

MODEL, VERSION = "BAAI/bge-m3", "int8-test"
DIM = 1024
HNSW_SQL = REPO_ROOT / "ai-service" / "scripts" / "create_hnsw_index.sql"


def _v(**truc: float) -> list[float]:
    """Vector đơn vị trên vài trục: ``_v(t0=0.9, t1=0.1)``. Cosine với ``_v(t0=1)`` = thành phần
    t0 sau chuẩn hoá — nên thứ hạng làn vector đọc được ngay từ tham số."""
    v = [0.0] * DIM
    for ten, gia_tri in truc.items():
        v[int(ten[1:])] = gia_tri
    do_dai = math.sqrt(sum(x * x for x in v))
    return [x / do_dai for x in v]


CAU_HOI = _v(t0=1)


# ── Hạ tầng test ─────────────────────────────────────────────────────────────


@pytest.fixture
async def factory(pg_dsn_ai_app) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Phiên bằng ``ai_app`` (chịu RLS). ``pool_size=1``: phiên sau dùng lại ĐÚNG kết nối của phiên
    trước — điều kiện để kiểm tham số HNSW không theo kết nối về pool."""
    engine = db_session.tao_engine(
        pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"),
        pool_size=1,
        max_overflow=0,
    )
    yield db_session.tao_session_factory(engine)
    await engine.dispose()


def _dsn_owner(pg_dsn_ai_app: str) -> str:
    return pg_dsn_ai_app.replace(f"{AI_USER}:{AI_PASSWORD}@", f"{OWNER_USER}:{OWNER_PASSWORD}@")


@pytest.fixture
async def factory_owner(pg_dsn_ai_app) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Phiên bằng ``crm_owner`` (``rolbypassrls = t``) — mô phỏng RLS bị vô hiệu. Dựng thẳng bằng
    ``create_async_engine`` vì ``tao_engine`` cố ý từ chối role này."""
    engine = create_async_engine(
        _dsn_owner(pg_dsn_ai_app).replace("postgresql://", "postgresql+psycopg://")
    )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture(scope="module")
def chi_muc_hnsw(pg_dsn_ai_app) -> None:
    """Dựng chỉ mục bằng CHÍNH câu lệnh trong ``create_hnsw_index.sql`` (bỏ ``CONCURRENTLY`` vì
    bảng test nhỏ). Đổi lớp toán tử ở script mà quên đổi toán tử ở ``hybrid.py`` là test đỏ."""
    cau_lenh = re.search(r"CREATE INDEX.*?;", HNSW_SQL.read_text(encoding="utf-8"), re.S)
    assert cau_lenh, "không tìm thấy CREATE INDEX trong create_hnsw_index.sql"
    with psycopg.connect(_dsn_owner(pg_dsn_ai_app), autocommit=True) as conn:
        conn.execute(cau_lenh.group(0).replace(" CONCURRENTLY", ""))


@asynccontextmanager
async def _giao_dich(factory) -> AsyncIterator[AsyncSession]:
    """Một transaction, rollback khi ra khỏi khối — kể cả khi test đạt."""
    async with factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()


async def _gan_tenant(session: AsyncSession, tenant: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant)}
    )


async def _tai_lieu(session: AsyncSession, *, status: str = "READY") -> UUID:
    """Một tài liệu của tenant đang gắn."""
    doc = uuid4()
    await session.execute(
        text(
            "INSERT INTO knowledge.knowledge_documents"
            " (id, tenant_id, title, source_type, file_path, file_name, status, error_message)"
            " VALUES (:id, ai.current_tenant(), :title, 'TXT', :path, :ten, :status, :loi)"
        ),
        {
            "id": doc,
            "title": f"Tài liệu {doc}",
            "path": f"/test/{doc}.txt",
            "ten": f"{doc}.txt",
            "status": status,
            "loi": "PARSE_FAILED" if status == "FAILED" else None,
        },
    )
    return doc


async def _doan(
    session: AsyncSession,
    doc: UUID,
    chi_so: int,
    noi_dung: str,
    vector: list[float],
    *,
    model: str = MODEL,
    version: str = VERSION,
) -> UUID:
    ma = uuid4()
    await session.execute(
        text(
            "INSERT INTO knowledge.knowledge_chunks (id, tenant_id, document_id, chunk_index,"
            " content, embedding, embedding_model, embedding_version) VALUES (:id,"
            " ai.current_tenant(), :doc, :i, :nd, CAST(:v AS vector), :model, :version)"
        ),
        {
            "id": ma,
            "doc": doc,
            "i": chi_so,
            "nd": noi_dung,
            "v": vector_sang_chuoi(vector),
            "model": model,
            "version": version,
        },
    )
    return ma


async def _tim(session: AsyncSession, cau_hoi: str | None = None, *, vector=CAU_HOI, **kw):
    return await tim_kiem_lai(
        session,
        vector=vector,
        tsquery=build_tsquery(cau_hoi) if cau_hoi else None,
        embedding_model=kw.pop("model", MODEL),
        embedding_version=kw.pop("version", VERSION),
        **kw,
    )


# ── Cô lập tenant ────────────────────────────────────────────────────────────


async def _hai_tenant_giong_het(session: AsyncSession) -> tuple[UUID, UUID]:
    """Hai tenant, cùng nội dung + cùng vector — ca khó nhất: mọi láng giềng đều "đúng"."""
    a, b = uuid4(), uuid4()
    for tenant in (a, b):
        await _gan_tenant(session, tenant)
        doc = await _tai_lieu(session)
        for i in range(4):
            await _doan(session, doc, i, f"Bảo hành máy lạnh {i} năm", _v(t0=4 - i, t1=1))
    return a, b


async def _cac_tenant_cua(session: AsyncSession, ket_qua) -> set[UUID]:
    ids = [d.chunk_id for d in ket_qua]
    dong = await session.execute(
        text("SELECT DISTINCT tenant_id FROM knowledge.knowledge_chunks WHERE id = ANY(:ids)"),
        {"ids": ids},
    )
    return {r[0] for r in dong}


async def test_chi_tra_doan_cua_tenant_dang_gan(factory):
    async with _giao_dich(factory) as s:
        a, _ = await _hai_tenant_giong_het(s)
        await _gan_tenant(s, a)
        ket_qua = await _tim(s, "bảo hành máy lạnh", k=10)
        assert len(ket_qua) == 4  # đủ 4 đoạn của A, không một đoạn nào của B
        assert await _cac_tenant_cua(s, ket_qua) == {a}


async def test_hang_rao_thu_hai_khi_rls_bi_bo_qua(factory_owner):
    """``crm_owner`` bỏ qua RLS. Chỉ còn ``c.tenant_id = ai.current_tenant()`` trong câu SQL chặn —
    xoá điều kiện đó khỏi ``hybrid.py`` thì test này đỏ, còn test ở trên vẫn xanh nhờ RLS."""
    async with _giao_dich(factory_owner) as s:
        a, _ = await _hai_tenant_giong_het(s)
        await _gan_tenant(s, a)
        for cau_hoi, vector in (("bảo hành máy lạnh", None), (None, CAU_HOI)):
            ket_qua = await _tim(s, cau_hoi, vector=vector, k=10)
            assert len(ket_qua) == 4
            assert await _cac_tenant_cua(s, ket_qua) == {a}


# ── Lọc trạng thái và thế hệ nhúng ───────────────────────────────────────────


@pytest.mark.parametrize("status", ["PENDING", "PROCESSING", "FAILED", "ARCHIVED"])
@pytest.mark.parametrize("lan", ["vector", "tu_khoa"])
async def test_bo_doan_cua_tai_lieu_chua_ready(factory, status, lan):
    """Đoạn của tài liệu không ``READY`` gần câu hỏi NHẤT ở cả hai làn — vẫn không được lọt."""
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        san_sang = await _tai_lieu(s)
        await _doan(s, san_sang, 0, "Đổi trả trong 7 ngày", _v(t0=1, t1=3))
        chua = await _tai_lieu(s, status=status)
        await _doan(s, chua, 0, "Đổi trả đổi trả đổi trả trong 30 ngày", _v(t0=1))
        ket_qua = await (
            _tim(s, vector=CAU_HOI) if lan == "vector" else _tim(s, "đổi trả", vector=None)
        )
        assert [d.document_id for d in ket_qua] == [san_sang]


@pytest.mark.parametrize(
    ("model", "version"), [("mock-hash-1024", VERSION), (MODEL, "fp32-khac")]
)
@pytest.mark.parametrize("lan", ["vector", "tu_khoa"])
async def test_bo_doan_khac_the_he_nhung(factory, model, version, lan):
    """Khác model HAY chỉ khác version đều là không gian vector khác — không được trộn."""
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        dung = await _doan(s, doc, 0, "Trả góp 0% qua thẻ", _v(t0=1, t1=3))
        await _doan(
            s, doc, 1, "Trả góp trả góp 0% lãi suất", _v(t0=1), model=model, version=version
        )
        ket_qua = await (
            _tim(s, vector=CAU_HOI) if lan == "vector" else _tim(s, "trả góp", vector=None)
        )
        assert [d.chunk_id for d in ket_qua] == [dung]


async def test_lan_vector_bo_doan_chua_co_vector(factory):
    """Quét tuần tự (kho nhỏ) xếp khoảng cách NULL xuống cuối nhưng VẪN trả về; HNSW thì không bao
    giờ chứa chúng. Không lọc thì kết quả phụ thuộc planner chọn đường nào."""
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        co = await _doan(s, doc, 0, "Giờ mở cửa 8h", _v(t0=1))
        await s.execute(
            text(
                "INSERT INTO knowledge.knowledge_chunks (tenant_id, document_id, chunk_index,"
                " content, embedding_model, embedding_version) VALUES (ai.current_tenant(),"
                " :doc, 1, 'Giờ đóng cửa 21h', :model, :version)"
            ),
            {"doc": doc, "model": MODEL, "version": VERSION},
        )
        assert [d.chunk_id for d in await _tim(s, vector=CAU_HOI)] == [co]


# ── RRF ──────────────────────────────────────────────────────────────────────


async def test_dong_thuan_hai_lan_thang_hang_nhat_mot_lan(factory):
    """Hạng 3 ở CẢ HAI làn (1/63 + 1/63) thắng hạng 1 ở MỘT làn (1/61).

    Cộng điểm thô thì không ra được điều này: cosine ~0,9 lấn át ``ts_rank`` ~0,1, và đoạn đứng
    đầu làn vector thắng bất kể làn từ khoá nói gì.
    """
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        # Làn vector (trục t0 giảm dần): v1 > v2 > dong_thuan. Không đoạn nào chứa chữ "inverter"
        # ngoài dong_thuan và hai đoạn chỉ-từ-khoá.
        v1 = await _doan(s, doc, 0, "Tủ lạnh 2 cửa", _v(t0=10, t1=1))
        await _doan(s, doc, 1, "Tủ lạnh 4 cửa", _v(t0=9, t1=1))
        dong_thuan = await _doan(s, doc, 2, "máy lạnh inverter", _v(t0=8, t1=1))
        # Làn từ khoá: nhiều lần "inverter" hơn → ts_rank cao hơn, nhưng vector xa câu hỏi.
        await _doan(s, doc, 3, "inverter inverter inverter inverter", _v(t1=1))
        await _doan(s, doc, 4, "inverter inverter inverter bền", _v(t2=1))

        # 3 ứng viên mỗi làn: kho chỉ có 5 đoạn, để 30 thì làn vector ôm hết cả 5.
        ket_qua = await _tim(s, "inverter", k=5, ung_vien=3)
        theo_id = {d.chunk_id: d for d in ket_qua}
        assert (theo_id[dong_thuan].hang_vector, theo_id[dong_thuan].hang_tu_khoa) == (3, 3)
        assert (theo_id[v1].hang_vector, theo_id[v1].hang_tu_khoa) == (1, None)
        assert ket_qua[0].chunk_id == dong_thuan


async def test_rrf_khac_cong_diem_tho(factory):
    """Ca hai cách xếp BẤT ĐỒNG. Cộng điểm thô: cosine 0,995 của đoạn đứng đầu làn vector lấn át
    ``ts_rank`` 0,08 của từ đơn. RRF: đoạn đứng đầu làn từ khoá VÀ có mặt ở làn vector thắng.

    Thang của ``ts_rank`` còn đổi theo DẠNG câu hỏi (đo thật trên Postgres 16): từ đơn
    "inverter" ×3 → 0,083; mã ``NH-TL256I`` ×3 — thành cụm liền kề ``nh-tl256i <-> nh <-> tl256i``
    — → 0,931. Cộng thẳng thì làn nào quyết định tuỳ câu hỏi có mã sản phẩm hay không. RRF chỉ
    nhìn thứ hạng nên không phụ thuộc thang (ADR-0006).
    """
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        dau_vector = await _doan(s, doc, 0, "Tủ lạnh 2 cửa", _v(t0=10, t1=1))  # cos 0,995
        await _doan(s, doc, 1, "Tủ lạnh 4 cửa", _v(t0=9, t1=1))  # cos 0,994
        dau_tu_khoa = await _doan(s, doc, 2, "inverter inverter inverter", _v(t0=1, t1=1.7))
        await _doan(s, doc, 3, "máy lạnh inverter", _v(t2=1))  # cos 0 — ngoài top-3 làn vector

        ket_qua = await _tim(s, "inverter", k=4, ung_vien=3)
        theo_id = {d.chunk_id: d for d in ket_qua}
        assert (theo_id[dau_tu_khoa].hang_vector, theo_id[dau_tu_khoa].hang_tu_khoa) == (3, 1)
        assert (theo_id[dau_vector].hang_vector, theo_id[dau_vector].hang_tu_khoa) == (1, None)
        assert ket_qua[0].chunk_id == dau_tu_khoa


async def test_diem_rrf_chi_tinh_tu_thu_hang(factory):
    """``diem_rrf`` = Σ 1/(60 + hạng) trên đúng các làn có mặt, và kết quả xếp giảm dần theo nó."""
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        for i in range(8):
            noi_dung = "phí giao hàng " * (i % 3 + 1) if i % 2 else f"lắp đặt {i}"
            await _doan(s, doc, i, noi_dung, _v(t0=8 - i, t1=i + 1))
        ket_qua = await _tim(s, "phí giao hàng", k=8)
        for d in ket_qua:
            mong_doi = sum(1 / (RRF_K + h) for h in (d.hang_vector, d.hang_tu_khoa) if h)
            assert d.diem_rrf == pytest.approx(mong_doi)
        assert [d.diem_rrf for d in ket_qua] == sorted((d.diem_rrf for d in ket_qua), reverse=True)


async def test_mot_lan_giu_nguyen_thu_hang_cua_lan_do(factory):
    """Chế độ dense-only / sparse-only của E3 là CÙNG câu SQL tắt một làn — thứ tự ra phải đúng
    thứ tự của riêng làn đó."""
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        ids = [
            await _doan(s, doc, i, "bảo hành " * (i + 1), _v(t0=1, t1=i + 1)) for i in range(5)
        ]
        chi_vector = await _tim(s, vector=CAU_HOI)
        assert [d.chunk_id for d in chi_vector] == ids  # t1 tăng dần → cosine giảm dần
        assert all(d.hang_tu_khoa is None for d in chi_vector)
        chi_tu_khoa = await _tim(s, "bảo hành", vector=None)
        assert [d.chunk_id for d in chi_tu_khoa] == ids[::-1]  # nhiều lần lặp → ts_rank cao hơn
        assert all(d.hang_vector is None for d in chi_tu_khoa)


async def test_ca_hai_lan_tat_thi_rong(factory):
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        assert await _tim(s, None, vector=None) == []


# ── Tham số HNSW và kế hoạch truy vấn ────────────────────────────────────────


async def _cai_dat(session: AsyncSession) -> tuple[str, str, str]:
    dong = await session.execute(
        text(
            "SELECT current_setting('hnsw.ef_search'), current_setting('hnsw.iterative_scan'),"
            " current_setting('plan_cache_mode')"
        )
    )
    return tuple(dong.one())


async def test_tham_so_hnsw_chet_theo_transaction(factory):
    """Trong transaction: đúng giá trị đã đặt. Transaction sau trên CÙNG kết nối (pool 1): về mặc
    định — không theo kết nối về pool mà ảnh hưởng request kế tiếp.

    Transaction đầu COMMIT như ``get_tenant_session``, không rollback: rollback hoàn tác cả một
    ``set_config`` cấp phiên, nên test dùng rollback không phân biệt được LOCAL với không LOCAL.
    Kho rỗng nên commit không để lại dòng nào.
    """
    async with factory() as s, s.begin():
        await _gan_tenant(s, uuid4())
        await _tim(s, "bảo hành")
        assert await _cai_dat(s) == ("100", "relaxed_order", "force_custom_plan")
    async with _giao_dich(factory) as s:
        assert await _cai_dat(s) == ("40", "off", "auto")


async def test_lan_vector_dung_chi_muc_hnsw(factory, chi_muc_hnsw):
    """Cấm quét tuần tự và cấm sắp xếp: làn vector chỉ còn một đường rẻ là quét chỉ mục HNSW theo
    thứ tự khoảng cách. Toán tử lệch lớp toán tử (``<->`` trên ``vector_cosine_ops``) thì không
    có đường đó, và kế hoạch không nhắc tới ``ix_chunk_embedding``."""
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        for i in range(20):
            await _doan(s, doc, i, f"đoạn {i}", _v(t0=1, t1=i + 1))
        await hybrid.dat_tham_so_truy_hoi(s)
        await s.execute(text("SET LOCAL enable_seqscan = off"))
        await s.execute(text("SET LOCAL enable_sort = off"))
        ke_hoach = await s.execute(
            text("EXPLAIN " + hybrid._SQL_TIM_LAI.text),
            {
                "vector": vector_sang_chuoi(CAU_HOI),
                "tsquery": None,
                "embedding_model": MODEL,
                "embedding_version": VERSION,
                "ung_vien": 30,
                "rrf_k": RRF_K,
                "k": 5,
            },
        )
        assert "ix_chunk_embedding" in "\n".join(r[0] for r in ke_hoach)


async def test_quet_lap_cuu_tenant_nho_trong_kho_dong(factory, chi_muc_hnsw):
    """HNSW lọc tenant SAU khi quét. Tenant nhỏ (5 đoạn) nằm cạnh 300 đoạn của tenant khác GẦN câu
    hỏi hơn: ``ef_search`` ứng viên đầu toàn của tenant khác. Tắt quét lặp → hụt; bật → đủ 5.

    Đây là cơ chế đằng sau phép so 1 ↔ 20 tenant của Ngày 6.
    """
    async with _giao_dich(factory) as s:
        await _gan_tenant(s, uuid4())
        doc = await _tai_lieu(s)
        for i in range(300):
            await _doan(s, doc, i, f"tenant đông {i}", _v(t0=50, t1=1 + i / 100, t3=i % 7))
        nho = uuid4()
        await _gan_tenant(s, nho)
        doc_nho = await _tai_lieu(s)
        for i in range(5):
            await _doan(s, doc_nho, i, f"tenant nhỏ {i}", _v(t0=1, t2=1 + i))

        async def dem(quet_lap: str) -> int:
            await s.execute(text("SET LOCAL enable_seqscan = off"))
            await s.execute(text("SET LOCAL enable_sort = off"))
            return len(await _tim(s, vector=CAU_HOI, k=5, ef_search=40, quet_lap=quet_lap))

        assert await dem("off") < 5
        assert await dem("relaxed_order") == 5
