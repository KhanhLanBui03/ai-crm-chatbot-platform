"""Ghi lượt (UC022 bước 9), đánh giá (UC027), khoảng trống tri thức (UC025) — Postgres THẬT, role
``ai_app`` chịu RLS.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Tenant B gắn đánh giá được vào lượt của tenant A không? → ``test_danh_gia_luot_tenant_khac_404``,
  và vì sao phải viết ``INSERT … SELECT`` → ``test_khoa_ngoai_khong_chiu_rls``.
- Tỉ lệ tích cực chia cho cái gì? → ``test_ty_le_tich_cuc_chia_cho_so_luot_co_danh_gia``.
- Mẫu 5% chọn thế nào, chạy lại có ra cùng tập không? → ``test_chon_mau_sql_khop_python``.
- Hàm DEFINER thứ hai có hẹp như hàm thứ nhất không? → ``test_ham_cham_chi_ai_app_goi_duoc…``.

Mỗi test dùng tenant ngẫu nhiên riêng: CSDL test sống suốt phiên pytest, RLS tách dữ liệu giữa các
test như tách giữa các khách hàng thật.
"""

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest

from src.ai import service
from src.ai.config import Settings
from src.ai.db import session as db_session
from src.ai.db.repositories import feedback_repository, interaction_repository
from src.ai.exceptions import InteractionNotFoundError
from src.ai.integrations.llm import CircuitBreaker, LLMChiuLoi, MockLLMClient
from src.ai.orchestrator.ghi_luot import DbTurnRecorder
from src.ai.orchestrator.turn import TurnRecord
from src.ai.rag.danh_gia.cham_tu_dong import mau_cham
from src.ai.schemas import FeedbackRequest
from src.ai.telemetry.metrics import turn_record_failures
from src.api import deps
from src.api.main import create_app
from tests.conftest import (
    AI_PASSWORD,
    AI_USER,
    CHUNK_A,
    OWNER_PASSWORD,
    OWNER_USER,
    TENANT_A,
    TENANT_B,
)


@pytest.fixture
async def factory(pg_dsn_ai_app):
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    yield db_session.tao_session_factory(engine)
    await engine.dispose()


def _owner(dsn: str) -> str:
    return dsn.replace(f"{AI_USER}:{AI_PASSWORD}@", f"{OWNER_USER}:{OWNER_PASSWORD}@")


def _ban_ghi(tenant: UUID | str, **thay) -> TurnRecord:
    goc = dict(
        interaction_id=uuid4(), tenant_id=str(tenant), conversation_id=str(uuid4()),
        branch="RAG", intent="KB_SEARCH", intent_confidence=0.9,
        user_query="máy lạnh bảo hành bao lâu", response_text="Dạ 24 tháng [1].",
        retrieved_chunk_ids=[], is_answered=True, refusal_reason=None,
        model_name="gemini-3.5-flash-lite", model_version=None, cost_vnd=0.0, latency_ms=1500,
        status="SUCCESS", error_message=None, safety_flag=None, llm_called=True,
        route_reason="KNOWLEDGE_QUERY", retrieval_top_score=0.71, groundedness_score=1.0,
        prompt_tokens=900, completion_tokens=40, degraded=False, handoff=False,
    )
    goc.update(thay)
    return TurnRecord(**goc)


def _tu_choi(tenant, cau: str, ly_do: str = "NOT_COVERED", **thay) -> TurnRecord:
    return _ban_ghi(
        tenant, user_query=cau, is_answered=False, refusal_reason=ly_do, llm_called=False,
        response_text="Dạ hiện em chưa tìm thấy…", groundedness_score=None, **thay
    )


async def _ghi(factory, *cac_ban_ghi: TurnRecord) -> list[UUID]:
    ghi = DbTurnRecorder(factory)
    for r in cac_ban_ghi:
        await ghi.record(r)
    return [r.interaction_id for r in cac_ban_ghi]


async def _gio_csdl(factory) -> datetime:
    """Mốc ``tu`` đo bằng đồng hồ CSDL — cùng đồng hồ với ``created_at``."""
    from sqlalchemy import text

    async with db_session.get_system_session(factory) as phien:
        return (await phien.execute(text("SELECT clock_timestamp()"))).scalar_one()


async def _dem(factory, tenant, sql: str, **tham_so) -> int:
    from sqlalchemy import text

    async with db_session.get_tenant_session(str(tenant), factory) as phien:
        return (await phien.execute(text(sql), tham_so)).scalar_one()


# ── Ghi lượt ─────────────────────────────────────────────────────────────────


async def test_ghi_luot_va_rls(factory):
    [ma] = await _ghi(factory, _ban_ghi(TENANT_A, safety_flag="CROSS_TENANT_PROBE",
                                        handoff=True, degraded=True))
    sql = "SELECT count(*) FROM ai.ai_interactions WHERE id = :id"
    assert await _dem(factory, TENANT_A, sql, id=ma) == 1
    assert await _dem(factory, TENANT_B, sql, id=ma) == 0
    with psycopg.connect(_owner(factory.kw["bind"].url.render_as_string(hide_password=False)
                                .replace("postgresql+psycopg://", "postgresql://"))) as conn:
        dong = conn.execute(
            "SELECT tenant_id, safety_flag, is_handoff, is_degraded, llm_called, total_tokens "
            "FROM ai.ai_interactions WHERE id = %s", (ma,)
        ).fetchone()
    assert dong == (TENANT_A, "CROSS_TENANT_PROBE", True, True, True, 940)


async def test_ghi_luot_hong_khong_nem_loi_ma_dem_metric(factory):
    truoc = turn_record_failures._value.get()
    # tenant không phải UUID ⇒ ai.current_tenant() ném — telemetry hỏng, lượt chat không được hỏng.
    await DbTurnRecorder(factory).record(_ban_ghi("khong-phai-uuid"))
    assert turn_record_failures._value.get() == truoc + 1


async def test_dem_tu_choi_lien_tiep(factory):
    t, hoi_thoai = uuid4(), str(uuid4())
    await _ghi(factory, _ban_ghi(t, conversation_id=hoi_thoai))
    for cau in ("a", "b"):
        await _ghi(factory, _tu_choi(t, cau, conversation_id=hoi_thoai))
    async with db_session.get_tenant_session(str(t), factory) as phien:
        assert await interaction_repository.dem_tu_choi_lien_tiep(phien, hoi_thoai) == 2
    await _ghi(factory, _ban_ghi(t, conversation_id=hoi_thoai))
    async with db_session.get_tenant_session(str(t), factory) as phien:
        assert await interaction_repository.dem_tu_choi_lien_tiep(phien, hoi_thoai) == 0


# ── Đánh giá — UC027 ─────────────────────────────────────────────────────────


async def _danh_gia(factory, tenant, yeu_cau: FeedbackRequest, ma: UUID | None = None):
    async with db_session.get_tenant_session(str(tenant), factory) as phien:
        return await service.record_feedback(phien, yeu_cau, ma)


async def test_danh_gia_lai_cung_phia_thi_cap_nhat(factory):
    [ma] = await _ghi(factory, _ban_ghi(TENANT_A))
    dau = await _danh_gia(factory, TENANT_A, FeedbackRequest(interaction_id=ma, rating=1))
    lai = await _danh_gia(factory, TENANT_A, FeedbackRequest(
        interaction_id=ma, rating=-1, reason_code="INCOMPLETE", comment="thiếu điều kiện"
    ))
    assert dau.created is True and lai.created is False
    assert lai.feedback_id == dau.feedback_id
    sql = "SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = :id AND rating = :r"
    assert await _dem(factory, TENANT_A, sql, id=ma, r="NEGATIVE") == 1
    assert await _dem(factory, TENANT_A, sql, id=ma, r="POSITIVE") == 0


async def test_moi_nhan_vien_mot_danh_gia_rieng(factory):
    [ma] = await _ghi(factory, _ban_ghi(TENANT_A))
    for nguoi in (uuid4(), uuid4()):
        await _danh_gia(factory, TENANT_A, FeedbackRequest(
            interaction_id=ma, rating=-1, reason_code="WRONG_INFO", rater_type="AGENT",
            rater_user_id=nguoi, corrected_answer="Bảo hành 24 tháng kể từ ngày lắp.",
        ))
    await _danh_gia(factory, TENANT_A, FeedbackRequest(interaction_id=ma, rating=1))
    sql = "SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = :id"
    assert await _dem(factory, TENANT_A, sql, id=ma) == 3


async def test_danh_gia_luot_tenant_khac_404(factory, pg_dsn_ai_app):
    [cua_a] = await _ghi(factory, _ban_ghi(TENANT_A))
    with pytest.raises(InteractionNotFoundError):
        await _danh_gia(factory, TENANT_B, FeedbackRequest(interaction_id=cua_a, rating=1))
    with psycopg.connect(_owner(pg_dsn_ai_app)) as conn:
        so = conn.execute(
            "SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = %s", (cua_a,)
        ).fetchone()[0]
    assert so == 0  # không một dòng nào lọt, kể cả dòng mang tenant_id của B


async def test_khoa_ngoai_khong_chiu_rls(factory, ai_conn):
    """Bằng chứng cho thiết kế của feedback_repository: kiểm khoá ngoại thấy MỌI dòng.

    Câu ``INSERT … VALUES`` thẳng từ phiên của tenant B, trỏ vào lượt của A, KHÔNG bị chặn — dòng
    mới mang tenant_id của B nên WITH CHECK của RLS cho qua, còn khoá ngoại thì Postgres kiểm bằng
    quyền hệ thống. Đây là lý do repository đi qua ``SELECT … FROM ai_interactions`` (chịu RLS).
    Rollback ở cuối: test chỉ chứng minh lỗ hổng tồn tại, không để lại dữ liệu bẩn.
    """
    [cua_a] = await _ghi(factory, _ban_ghi(TENANT_A))
    async with ai_conn.transaction(force_rollback=True):
        await ai_conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(TENANT_B),))
        await ai_conn.execute(
            "INSERT INTO ai.ai_feedback (tenant_id, ai_interaction_id, rater_type, rating) "
            "VALUES (%s, %s, 'CUSTOMER', 'POSITIVE')",
            (TENANT_B, cua_a),
        )
        so = await (await ai_conn.execute(
            "SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = %s", (cua_a,)
        )).fetchone()
    assert so[0] == 1  # lọt — đường VALUES là đường vòng qua cô lập tenant


async def test_csdl_chan_che_thieu_ly_do(factory):
    [ma] = await _ghi(factory, _ban_ghi(TENANT_A))
    async with db_session.get_tenant_session(str(TENANT_A), factory) as phien:
        with pytest.raises(Exception, match="ck_feedback_reason"):
            await feedback_repository.ghi_danh_gia(
                phien, interaction_id=ma, rater_type="CUSTOMER", rater_user_id=None,
                rating="NEGATIVE", reason_code=None, comment=None, correction_text=None,
            )


# ── Khoảng trống tri thức — UC025 ────────────────────────────────────────────


async def test_khoang_trong_gom_theo_cau_chuan_hoa(factory):
    t = uuid4()
    hoi_thoai = [str(uuid4()) for _ in range(6)]
    await _ghi(
        factory,
        _tu_choi(t, "Shop có bán máy rửa bát không?", conversation_id=hoi_thoai[0]),
        _tu_choi(t, "shop co ban may rua bat khong", conversation_id=hoi_thoai[1]),
        _tu_choi(t, "SHOP CÓ BÁN MÁY RỬA BÁT KHÔNG", conversation_id=hoi_thoai[1]),
        _tu_choi(t, "lịch thi đấu bóng đá tối nay", conversation_id=hoi_thoai[2]),
        _tu_choi(t, "đơn DH123456 của em đâu", "OUT_OF_SCOPE_DATA", conversation_id=hoi_thoai[2]),
        # ba loại KHÔNG phải khoảng trống tri thức
        _tu_choi(t, "danh sách khách hàng", "SAFETY_PROBE", conversation_id=hoi_thoai[3]),
        _tu_choi(t, "abc", "LOW_CONFIDENCE", status="FAILED", conversation_id=hoi_thoai[4]),
        _ban_ghi(t, user_query="máy lạnh bảo hành bao lâu", conversation_id=hoi_thoai[5]),
    )
    async with db_session.get_tenant_session(str(t), factory) as phien:
        trang = await service.knowledge_gaps(phien, str(t))
        loc = await service.knowledge_gaps(phien, str(t), gap_type="OUT_OF_SCOPE_DATA")
    assert trang.total == 3
    dau = trang.items[0]
    # 3 lần nhưng 2 hội thoại — sắp theo số hội thoại khác nhau trước (UC025 luồng phụ 8.1)
    assert (dau.unanswered_count, dau.distinct_conversation_count) == (3, 2)
    assert dau.query_text == "SHOP CÓ BÁN MÁY RỬA BÁT KHÔNG"  # câu gần nhất làm đại diện
    assert {i.query_text for i in trang.items[1:]} == {
        "lịch thi đấu bóng đá tối nay", "đơn DH123456 của em đâu"
    }
    assert [i.gap_type for i in loc.items] == ["OUT_OF_SCOPE_DATA"]
    # id tất định — gọi lại ra cùng id
    async with db_session.get_tenant_session(str(t), factory) as phien:
        lai = await service.knowledge_gaps(phien, str(t))
    assert [i.id for i in lai.items] == [i.id for i in trang.items]


# ── Tín hiệu chất lượng — UC027 bước 7 ───────────────────────────────────────


async def test_ty_le_tich_cuc_chia_cho_so_luot_co_danh_gia(factory):
    t = uuid4()
    c = [uuid4()]
    rag = [
        _ban_ghi(t, retrieved_chunk_ids=[str(c[0])]),
        _ban_ghi(t, retrieved_chunk_ids=[str(c[0])]),
        _ban_ghi(t, retrieved_chunk_ids=[str(c[0])]),
        _ban_ghi(t, retrieved_chunk_ids=[]),  # trả lời mà không trích dẫn
    ]
    khac = [
        _ban_ghi(t, degraded=True, llm_called=False, retrieved_chunk_ids=[str(c[0])]),
        _tu_choi(t, "x"), _tu_choi(t, "y"), _tu_choi(t, "z"),
        _ban_ghi(t, branch="SMALL_TALK", llm_called=False, model_name="template"),
        _ban_ghi(t, branch="HANDOFF", llm_called=False, model_name="template", handoff=True),
        _tu_choi(t, "w", "LOW_CONFIDENCE", status="FAILED"),
    ]
    ma = await _ghi(factory, *rag, *khac)
    await _danh_gia(factory, t, FeedbackRequest(interaction_id=ma[0], rating=1))
    await _danh_gia(factory, t, FeedbackRequest(interaction_id=ma[1], rating=-1,
                                                reason_code="WRONG_INFO"))
    await _danh_gia(factory, t, FeedbackRequest(
        interaction_id=ma[1], rating=-1, reason_code="INCOMPLETE", rater_type="AGENT",
        rater_user_id=uuid4(),
    ))
    bay_gio = datetime.now(UTC)
    async with db_session.get_tenant_session(str(t), factory) as phien:
        q = await service.quality_summary(phien, bay_gio - timedelta(hours=1),
                                          bay_gio + timedelta(hours=1))
    assert (q.so_luot, q.so_luot_loi) == (10, 1)
    assert (q.ty_le_tu_choi.tu_so, q.ty_le_tu_choi.mau_so) == (3, 10)
    assert q.ty_le_suy_giam.gia_tri == 0.1 and q.ty_le_chuyen_giao.gia_tri == 0.1
    assert (q.ty_le_khong_goi_llm.tu_so, q.ty_le_khong_goi_llm.mau_so) == (6, 10)
    # suy giảm có trích dẫn nhưng KHÔNG vào độ phủ — 3/4, không phải 4/5
    assert (q.do_phu_trich_dan.tu_so, q.do_phu_trich_dan.mau_so) == (3, 4)
    khach = next(d for d in q.danh_gia if d.rater_type == "CUSTOMER")
    # 1 khen / 2 lượt CÓ đánh giá của khách = 0,5 — chia cho 10 lượt thì ra 0,1 vô nghĩa
    assert (khach.ty_le_tich_cuc.tu_so, khach.ty_le_tich_cuc.mau_so) == (1, 2)
    assert khach.ty_le_tich_cuc.gia_tri == 0.5 and khach.che_theo_ly_do == {"WRONG_INFO": 1}
    nhan_vien = next(d for d in q.danh_gia if d.rater_type == "AGENT")
    assert nhan_vien.ty_le_tich_cuc.gia_tri == 0.0


# ── Bộ chấm tự động — UC027 bước 6 ───────────────────────────────────────────


def test_ham_cham_chi_ai_app_goi_duoc_va_ghim_search_path(pg_dsn_ai_app):
    """Cùng bốn chốt với knowledge.tim_job_ket (V211) — database.md: hàm DEFINER thứ hai."""
    with psycopg.connect(pg_dsn_ai_app) as conn:
        dinh_nghia, cau_hinh, crm_app, ai_app = conn.execute(
            """
            SELECT p.prosecdef, p.proconfig,
                   has_function_privilege('crm_app', p.oid, 'EXECUTE'),
                   has_function_privilege('ai_app', p.oid, 'EXECUTE')
              FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'ai' AND p.proname = 'tim_luot_can_cham'
            """
        ).fetchone()
        so_cot = len(conn.execute(
            "SELECT * FROM ai.tim_luot_can_cham(now(), 0.05, 1)"
        ).description)
    assert dinh_nghia is True
    assert cau_hinh == ["search_path=pg_catalog, pg_temp"]
    assert (crm_app, ai_app) == (False, True)
    assert so_cot == 3  # tenant_id, interaction_id, created_at — không câu hỏi, không câu trả lời


async def test_chon_mau_sql_khop_python(factory):
    t = uuid4()
    tu = datetime.now(UTC) - timedelta(seconds=1)
    du_dieu_kien = [_ban_ghi(t) for _ in range(300)]
    # Bốn loại KHÔNG được chấm dù id rơi vào mẫu: từ chối, suy giảm, mẫu câu, không gọi LLM.
    khong_du = (
        [_tu_choi(t, "x") for _ in range(40)]
        + [_ban_ghi(t, degraded=True) for _ in range(40)]
        + [_ban_ghi(t, branch="SMALL_TALK", llm_called=False) for _ in range(40)]
    )
    await _ghi(factory, *du_dieu_kien, *khong_du)
    async with db_session.get_system_session(factory) as phien:
        lan_1, _ = await interaction_repository.tim_luot_can_cham(phien, tu, 0.05, 200)
        lan_2, _ = await interaction_repository.tim_luot_can_cham(phien, tu, 0.05, 200)
    cua_t = {r.interaction_id for r in lan_1 if r.tenant_id == t}
    mong_doi = {r.interaction_id for r in du_dieu_kien if mau_cham(r.interaction_id, 0.05)}
    assert cua_t == mong_doi and len(mong_doi) > 0
    assert {r.interaction_id for r in lan_2 if r.tenant_id == t} == cua_t  # tất định


async def test_cham_tu_dong_ghi_mau_va_bo_khi_khong_chac(factory, monkeypatch):
    # Lượt của TENANT_A trích CHUNK_A — đoạn có thật trong CSDL test, giám khảo có căn cứ để đọc.
    monkeypatch.setattr(
        service, "get_settings",
        lambda: Settings(cham_tu_dong_ty_le=1.0, cham_tu_dong_nguong_chac=0.7),
    )
    tu = await _gio_csdl(factory)
    [ma_chac] = await _ghi(factory, _ban_ghi(TENANT_A, retrieved_chunk_ids=[str(CHUNK_A)]))

    giam_khao = LLMChiuLoi(MockLLMClient(
        noi_dung='{"rating": "NEGATIVE", "reason_code": "INCOMPLETE", "do_chac": 0.9}'
    ), CircuitBreaker(), han_chot_s=5)
    kq = await service.cham_tu_dong_lo(giam_khao, tu=tu, factory=factory)
    assert (kq.so_ung_vien, kq.so_ghi) == (1, 1)
    sql = ("SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = :id "
           "AND rater_type = 'AUTO_EVAL' AND rater_user_id IS NULL AND reason_code = 'INCOMPLETE'")
    assert await _dem(factory, TENANT_A, sql, id=ma_chac) == 1

    # Đã chấm thì lần quét sau không lấy lại nữa, dù quét lại từ cùng mốc.
    lai = await service.cham_tu_dong_lo(giam_khao, tu=tu, factory=factory)
    assert (lai.so_ung_vien, lai.so_ghi) == (0, 0)

    [ma_khong_chac] = await _ghi(factory, _ban_ghi(TENANT_A, retrieved_chunk_ids=[str(CHUNK_A)]))
    do_du = LLMChiuLoi(MockLLMClient(
        noi_dung='{"rating": "POSITIVE", "do_chac": 0.4}'
    ), CircuitBreaker(), han_chot_s=5)
    kq = await service.cham_tu_dong_lo(do_du, tu=tu, factory=factory)
    assert (kq.so_ung_vien, kq.so_khong_chac) == (1, 1)
    sql2 = "SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = :id"
    assert await _dem(factory, TENANT_A, sql2, id=ma_khong_chac) == 0  # luồng phụ 6.1


async def test_cham_bo_qua_luot_khong_con_doan_can_cu(factory, monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: Settings(cham_tu_dong_ty_le=1.0))
    tu = await _gio_csdl(factory)
    [ma] = await _ghi(factory, _ban_ghi(TENANT_A, retrieved_chunk_ids=[str(uuid4())]))
    giam_khao = LLMChiuLoi(MockLLMClient(
        noi_dung='{"rating": "POSITIVE", "do_chac": 0.99}'
    ), CircuitBreaker(), han_chot_s=5)
    kq = await service.cham_tu_dong_lo(giam_khao, tu=tu, factory=factory)
    assert (kq.so_ung_vien, kq.so_bo_qua) == (1, 1)
    sql = "SELECT count(*) FROM ai.ai_feedback WHERE ai_interaction_id = :id"
    assert await _dem(factory, TENANT_A, sql, id=ma) == 0


# ── HTTP — mã lỗi theo đặc tả UC027 ──────────────────────────────────────────


@pytest.fixture
async def client(factory):
    async def _phien_test(tenant_id: deps.TenantIdDep):
        async with db_session.get_tenant_session(tenant_id, factory=factory) as phien:
            yield phien

    app = create_app()
    app.dependency_overrides[deps.get_session] = _phien_test
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_http_danh_gia_va_ma_loi(client, factory):
    [ma] = await _ghi(factory, _ban_ghi(TENANT_A))
    h_a, h_b = {"X-Tenant-Id": str(TENANT_A)}, {"X-Tenant-Id": str(TENANT_B)}

    r = await client.post("/v1/ai/feedback", json={"interaction_id": str(ma), "rating": 1},
                          headers=h_a)
    assert r.status_code == 200 and r.json()["created"] is True

    r = await client.post(f"/v1/ai-interactions/{ma}/feedback",
                          json={"rating": -1, "reason_code": "IRRELEVANT"}, headers=h_a)
    assert r.status_code == 200 and r.json()["created"] is False

    r = await client.post(f"/v1/ai-interactions/{ma}/feedback", json={"rating": -1}, headers=h_a)
    assert (r.status_code, r.json()["code"]) == (422, "REASON_REQUIRED")

    r = await client.post("/v1/ai/feedback", json={"interaction_id": str(ma), "rating": 1},
                          headers=h_b)
    assert (r.status_code, r.json()["code"]) == (404, "INTERACTION_NOT_FOUND")

    r = await client.post(
        "/v1/ai/feedback",
        json={"interaction_id": str(ma), "rating": 1, "tenant_id": str(TENANT_B)}, headers=h_a,
    )
    assert (r.status_code, r.json()["code"]) == (422, "INVALID_FEEDBACK")

    r = await client.post(
        "/v1/ai/feedback",
        json={"interaction_id": str(ma), "rating": -1, "reason_code": "BAD_TONE",
              "rater_type": "AGENT"}, headers=h_a,
    )
    assert (r.status_code, r.json()["code"]) == (422, "INVALID_RATER")

    r = await client.post("/v1/ai/feedback", json={"rating": 1}, headers={})
    assert r.status_code == 401


async def test_http_khoang_trong_va_tin_hieu(client, factory):
    t = uuid.uuid4()
    await _ghi(factory, _tu_choi(t, "có bán máy pha cà phê không"))
    h = {"X-Tenant-Id": str(t)}
    r = await client.get("/v1/knowledge-gaps", headers=h)
    assert r.status_code == 200
    assert [i["query_text"] for i in r.json()["items"]] == ["có bán máy pha cà phê không"]
    r = await client.get("/v1/ai/quality", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["so_luot"] == 1 and d["ty_le_tu_choi"] == {"tu_so": 1, "mau_so": 1, "gia_tri": 1.0}


async def test_lo_day_thi_moc_tiep_khong_nhay_qua_ung_vien_con_lai(factory, monkeypatch):
    """Lỗi bắt được Ngày 10: trần 50/lô mà mốc dời thẳng tới "bây giờ" là bỏ rơi phần vượt trần."""
    monkeypatch.setattr(
        service, "get_settings",
        lambda: Settings(cham_tu_dong_ty_le=1.0, cham_tu_dong_toi_da=3),
    )
    tu = await _gio_csdl(factory)
    ma = await _ghi(factory, *[_ban_ghi(uuid4(), retrieved_chunk_ids=[str(uuid4())])
                               for _ in range(5)])
    giam_khao = LLMChiuLoi(MockLLMClient(noi_dung="{}"), CircuitBreaker(), han_chot_s=5)
    dau = await service.cham_tu_dong_lo(giam_khao, tu=tu, factory=factory)
    assert dau.so_ung_vien == 3
    sau = await service.cham_tu_dong_lo(giam_khao, tu=dau.moc_tiep, factory=factory)
    # Lượt cuối của lô đầu được xét lại một lần (cùng created_at) — đổi lại không lượt nào bị bỏ.
    async with db_session.get_system_session(factory) as phien:
        con_lai, _ = await interaction_repository.tim_luot_can_cham(phien, dau.moc_tiep, 1.0, 200)
    assert set(ma[3:]) <= {r.interaction_id for r in con_lai}
    assert sau.so_ung_vien >= 2
