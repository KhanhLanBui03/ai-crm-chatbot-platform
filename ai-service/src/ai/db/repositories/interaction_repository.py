"""Lượt xử lý của tác tử — ``ai.ai_interactions`` (V204, V208, V209, V212). [PRODUCTION]

Ghi một dòng mỗi lượt chat (UC022 bước 9), rồi đọc lại cho ba việc:

- UC025: đếm lượt từ chối liên tiếp trong một hội thoại; danh sách khoảng trống tri thức.
- UC027: tổng hợp tín hiệu rẻ (100% lượt) và tỉ lệ đánh giá tích cực.
- UC027: đọc nội dung một lượt để bộ chấm tự động chấm.

Lọc tenant để RLS lo (``get_tenant_session``) — không tự thêm ``WHERE tenant_id``, như mọi
repository khác của Track B. Riêng ``tim_luot_can_cham`` gọi hàm ``SECURITY DEFINER`` của V212.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Ba lý do là KHOẢNG TRỐNG TRI THỨC (enum LoaiKhoangTrong của dashboard-api.yaml). SAFETY_PROBE
# không phải: thêm tài liệu không bao giờ "lấp" được một câu dò dữ liệu khách hàng khác.
LY_DO_KHOANG_TRONG = ("NOT_COVERED", "OUT_OF_SCOPE_DATA", "LOW_CONFIDENCE")

_SQL_GHI_LUOT = text(
    """
    INSERT INTO ai.ai_interactions (
        id, tenant_id, conversation_id, branch, intent, intent_confidence, user_query,
        response_text, retrieved_chunk_ids, retrieval_top_score, is_answered, refusal_reason,
        model_name, model_version, prompt_tokens, completion_tokens, total_tokens, cost_vnd,
        latency_ms, status, error_message, safety_flag, groundedness_score,
        llm_called, is_degraded, is_handoff
    ) VALUES (
        :id, ai.current_tenant(), :conversation_id, :branch, :intent, :intent_confidence,
        :user_query, :response_text, :retrieved_chunk_ids, :retrieval_top_score, :is_answered,
        :refusal_reason, :model_name, :model_version, :prompt_tokens, :completion_tokens,
        :total_tokens, :cost_vnd, :latency_ms, :status, :error_message, :safety_flag,
        :groundedness_score, :llm_called, :is_degraded, :is_handoff
    )
    """
)


def _lam_tron(gia_tri: float | None, so_le: int) -> float | None:
    """Khớp ``numeric(p, s)`` của cột — để CSDL không tự làm tròn khác Python."""
    return None if gia_tri is None else round(gia_tri, so_le)


async def ghi_luot(
    session: AsyncSession,
    *,
    id: UUID,
    conversation_id: str,
    branch: str,
    intent: str | None,
    intent_confidence: float | None,
    user_query: str,
    response_text: str | None,
    retrieved_chunk_ids: Sequence[str],
    retrieval_top_score: float | None,
    is_answered: bool,
    refusal_reason: str | None,
    model_name: str,
    model_version: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cost_vnd: float,
    latency_ms: int,
    status: str,
    error_message: str | None,
    safety_flag: str | None,
    groundedness_score: float | None,
    llm_called: bool,
    is_degraded: bool,
    is_handoff: bool,
) -> None:
    """Một dòng ``ai_interactions``. ``user_query`` phải ĐÃ che PII (``_build_record`` lo)."""
    vao, ra = prompt_tokens or 0, completion_tokens or 0
    await session.execute(
        _SQL_GHI_LUOT,
        {
            "id": id,
            "conversation_id": conversation_id,
            "branch": branch,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "user_query": user_query,
            "response_text": response_text,
            "retrieved_chunk_ids": [UUID(str(c)) for c in retrieved_chunk_ids],
            "retrieval_top_score": _lam_tron(retrieval_top_score, 4),
            "is_answered": is_answered,
            "refusal_reason": refusal_reason,
            "model_name": model_name,
            "model_version": model_version,
            "prompt_tokens": vao,
            "completion_tokens": ra,
            "total_tokens": vao + ra,
            "cost_vnd": _lam_tron(cost_vnd, 4),
            "latency_ms": latency_ms,
            "status": status,
            "error_message": error_message,
            "safety_flag": safety_flag,
            "groundedness_score": _lam_tron(groundedness_score, 3),
            "llm_called": llm_called,
            "is_degraded": is_degraded,
            "is_handoff": is_handoff,
        },
    )


async def dem_tu_choi_lien_tiep(
    session: AsyncSession, conversation_id: str, toi_da: int = 5
) -> int:
    """Số lượt GẦN NHẤT liên tiếp chưa trả lời được trong hội thoại (UC025 luồng phụ 3.3).

    Một lượt trả lời được (kể cả mẫu câu chào, câu hỏi lại) là cắt chuỗi: khách đã được giúp ở
    giữa thì hai lần từ chối hai đầu không phải "lặp lại thất bại".
    """
    ket_qua = await session.execute(
        text(
            """
            SELECT is_answered FROM ai.ai_interactions
             WHERE conversation_id = :c
             ORDER BY created_at DESC
             LIMIT :n
            """
        ),
        {"c": conversation_id, "n": toi_da},
    )
    dem = 0
    for (da_tra_loi,) in ket_qua.all():
        if da_tra_loi:
            break
        dem += 1
    return dem


# ── UC025 — khoảng trống tri thức ────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class KhoangTrong:
    khoa: str
    gap_type: str
    query_text: str
    unanswered_count: int
    distinct_conversation_count: int
    first_occurred_at: datetime
    last_occurred_at: datetime


async def khoang_trong_tri_thuc(
    session: AsyncSession,
    *,
    so_ngay: int,
    gap_type: str | None,
    gioi_han: int,
    bo_qua: int,
) -> tuple[list[KhoangTrong], int]:
    """Truy vấn GỘP — không có bảng ``knowledge_gaps`` (đặc tả UC025, dashboard-api SCR034).

    Gom theo câu hỏi đã chuẩn hoá CHUỖI: bỏ dấu (``knowledge.f_unaccent`` — cùng hàm làn từ khoá),
    viết thường, mọi ký tự không phải chữ/số thành một khoảng trắng. "Shop có bán máy rửa bát
    không?" và "shop co ban may rua bat khong" về một dòng; hai cách hỏi khác hẳn câu chữ thì vẫn
    hai dòng — đánh đổi đã ghi trong đặc tả (gom theo ngữ nghĩa là hướng mở rộng số 3).

    Chỉ lấy lượt ``SUCCESS``: lượt ``FAILED`` cũng mang ``LOW_CONFIDENCE`` (``_build_record``) nhưng
    đó là lỗi hệ thống, thêm tài liệu không sửa được. Cửa sổ ``so_ngay`` là cách một khoảng trống
    "tự biến mất" khi tài liệu mới đã nạp và lượt từ chối ngừng phát sinh — không có nút "đã xử lý".

    Sắp theo số HỘI THOẠI khác nhau trước, số lần sau (UC025 luồng phụ 8.1): một câu bị nhiều
    khách hỏi quan trọng hơn một khách hỏi đi hỏi lại. ``ai_interactions`` không có ``contact_id``
    (liên làn), nên "khách khác nhau" xấp xỉ bằng hội thoại khác nhau.
    """
    ket_qua = await session.execute(
        text(
            """
            WITH tu_choi AS (
                SELECT btrim(regexp_replace(
                           lower(knowledge.f_unaccent(coalesce(user_query, ''))),
                           '[^a-z0-9]+', ' ', 'g')) AS khoa,
                       refusal_reason, user_query, conversation_id, created_at
                  FROM ai.ai_interactions
                 WHERE NOT is_answered
                   AND status = 'SUCCESS'
                   AND refusal_reason = ANY(:cac_ly_do)
                   AND created_at >= now() - make_interval(days => :so_ngay)
            )
            SELECT khoa,
                   refusal_reason,
                   (array_agg(user_query ORDER BY created_at DESC))[1],
                   count(*),
                   count(DISTINCT conversation_id),
                   min(created_at),
                   max(created_at),
                   count(*) OVER ()
              FROM tu_choi
             WHERE khoa <> ''
             GROUP BY khoa, refusal_reason
             ORDER BY count(DISTINCT conversation_id) DESC, count(*) DESC, max(created_at) DESC
             LIMIT :gioi_han OFFSET :bo_qua
            """
        ),
        {
            "cac_ly_do": [gap_type] if gap_type else list(LY_DO_KHOANG_TRONG),
            "so_ngay": so_ngay,
            "gioi_han": gioi_han,
            "bo_qua": bo_qua,
        },
    )
    dong = ket_qua.all()
    tong = dong[0][7] if dong else 0
    return [KhoangTrong(*d[:7]) for d in dong], tong


# ── UC027 — tín hiệu rẻ và tỉ lệ đánh giá ────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TinHieuLuot:
    """Đếm trên lượt ``SUCCESS`` trong cửa sổ — mẫu số của từng tỉ lệ ghi ngay cạnh tên."""

    so_luot: int
    so_loi: int  # lượt FAILED/TIMEOUT — đếm riêng, không vào mẫu số nào bên dưới
    so_tu_choi: int  # / so_luot
    so_suy_giam: int  # / so_luot
    so_chuyen_giao: int  # / so_luot
    so_khong_goi_llm: int  # / so_luot — KPI ≥ 55% (§1.6)
    so_rag_tra_loi: int  # lượt RAG trả lời bằng LLM (không tính suy giảm)
    so_rag_co_trich_dan: int  # / so_rag_tra_loi — độ phủ trích dẫn
    groundedness_tb: float | None
    tu_choi_theo_ly_do: dict[str, int]


async def tin_hieu_luot(session: AsyncSession, tu: datetime, den: datetime) -> TinHieuLuot:
    """Bốn tín hiệu rẻ của UC027 — chạy trên 100% lượt vì chỉ là đếm cột đã ghi sẵn.

    BỎ nhánh ``SUMMARY`` (UC026, Ngày 12): đó là lượt NỀN của worker, không phải lượt chat. Gộp vào
    thì mỗi hội thoại đóng thêm một lượt "có gọi LLM" và KPI ≥ 55% lượt không gọi LLM (§1.6) tụt
    theo số hội thoại đã tóm tắt — đo sai đúng thứ nó được dựng ra để đo.

    Độ phủ trích dẫn tính trên lượt RAG trả lời bằng LLM, KHÔNG gồm lượt suy giảm: lượt suy giảm
    luôn có đúng một trích dẫn (chép nguyên văn đoạn), gộp vào thì chỉ số đẹp lên đúng lúc LLM sập.
    """
    ket_qua = await session.execute(
        text(
            """
            SELECT count(*) FILTER (WHERE status = 'SUCCESS'),
                   count(*) FILTER (WHERE status <> 'SUCCESS'),
                   count(*) FILTER (WHERE status = 'SUCCESS' AND NOT is_answered),
                   count(*) FILTER (WHERE status = 'SUCCESS' AND is_degraded),
                   count(*) FILTER (WHERE status = 'SUCCESS' AND is_handoff),
                   count(*) FILTER (WHERE status = 'SUCCESS' AND NOT llm_called),
                   count(*) FILTER (WHERE status = 'SUCCESS' AND branch = 'RAG' AND is_answered
                                      AND NOT is_degraded AND llm_called),
                   count(*) FILTER (WHERE status = 'SUCCESS' AND branch = 'RAG' AND is_answered
                                      AND NOT is_degraded AND llm_called
                                      AND cardinality(retrieved_chunk_ids) > 0),
                   avg(groundedness_score) FILTER (WHERE status = 'SUCCESS')
              FROM ai.ai_interactions
             WHERE created_at >= :tu AND created_at < :den
               AND branch <> 'SUMMARY'
            """
        ),
        {"tu": tu, "den": den},
    )
    d = ket_qua.one()
    theo_ly_do = await session.execute(
        text(
            """
            SELECT refusal_reason, count(*)
              FROM ai.ai_interactions
             WHERE created_at >= :tu AND created_at < :den
               AND status = 'SUCCESS' AND NOT is_answered AND branch <> 'SUMMARY'
             GROUP BY refusal_reason
            """
        ),
        {"tu": tu, "den": den},
    )
    tb = d[8]
    return TinHieuLuot(
        *d[:8],
        groundedness_tb=None if tb is None else round(float(tb), 3),
        tu_choi_theo_ly_do={ly_do: so for ly_do, so in theo_ly_do.all()},
    )


@dataclass(frozen=True, slots=True)
class DanhGiaTheoPhia:
    rater_type: str
    so_danh_gia: int
    so_tich_cuc: int
    che_theo_ly_do: dict[str, int]


async def danh_gia_theo_phia(
    session: AsyncSession, tu: datetime, den: datetime
) -> list[DanhGiaTheoPhia]:
    """Đếm đánh giá theo phía, trên lượt NẰM TRONG cửa sổ (theo thời điểm lượt, không thời điểm
    đánh giá — để tỉ lệ khớp được với tín hiệu rẻ cùng cửa sổ).

    Trả SỐ ĐẾM, không trả tỉ lệ: mẫu số của tỉ lệ tích cực là ``so_danh_gia`` (số lượt CÓ đánh giá
    từ phía đó), không phải tổng số lượt — tầng trên chia, và tên trường nói rõ chia cho cái gì.
    """
    ket_qua = await session.execute(
        text(
            """
            SELECT f.rater_type, f.rating, f.reason_code, count(*)
              FROM ai.ai_feedback f
              JOIN ai.ai_interactions i ON i.id = f.ai_interaction_id
             WHERE i.created_at >= :tu AND i.created_at < :den
             GROUP BY f.rater_type, f.rating, f.reason_code
            """
        ),
        {"tu": tu, "den": den},
    )
    gom: dict[str, dict[str, Any]] = {}
    for phia, danh_gia, ly_do, so in ket_qua.all():
        g = gom.setdefault(phia, {"so_danh_gia": 0, "so_tich_cuc": 0, "che": {}})
        g["so_danh_gia"] += so
        if danh_gia == "POSITIVE":
            g["so_tich_cuc"] += so
        elif ly_do:
            g["che"][ly_do] = g["che"].get(ly_do, 0) + so
    return [
        DanhGiaTheoPhia(phia, g["so_danh_gia"], g["so_tich_cuc"], g["che"])
        for phia, g in sorted(gom.items())
    ]


# ── UC027 — bộ chấm tự động ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class LuotCanCham:
    """Một dòng của ``ai.tim_luot_can_cham`` — chỉ định danh và thời điểm, không nội dung."""

    tenant_id: UUID
    interaction_id: UUID
    created_at: datetime


async def tim_luot_can_cham(
    session: AsyncSession, tu: datetime, ty_le: float, toi_da: int
) -> tuple[list[LuotCanCham], datetime]:
    """Gọi hàm ``SECURITY DEFINER`` của V212. ``session`` phải là phiên KHÔNG gắn tenant.

    Trả kèm giờ CSDL lúc quét: mốc quét lần sau phải đo bằng CÙNG đồng hồ với ``created_at`` —
    lấy giờ của máy chạy worker là cược rằng hai đồng hồ không lệch nhau.
    """
    bay_gio = (await session.execute(text("SELECT clock_timestamp()"))).scalar_one()
    ket_qua = await session.execute(
        text("SELECT * FROM ai.tim_luot_can_cham(:tu, :ty_le, :n)"),
        {"tu": tu, "ty_le": Decimal(str(ty_le)), "n": toi_da},
    )
    return [LuotCanCham(*d) for d in ket_qua.all()], bay_gio


@dataclass(frozen=True, slots=True)
class NoiDungLuot:
    user_query: str
    response_text: str
    cac_doan: list[str]  # nội dung các đoạn được trích, theo thứ tự trích dẫn


async def doc_luot_de_cham(session: AsyncSession, interaction_id: UUID) -> NoiDungLuot | None:
    """Câu hỏi (đã che PII lúc ghi), câu trả lời và nội dung các đoạn được trích.

    ``None`` khi lượt không còn, hoặc mọi đoạn được trích đã bị xoá/nạp lại — chấm một câu trả lời
    mà không còn căn cứ để đối chiếu là chấm mò.
    """
    luot = (
        await session.execute(
            text(
                """
                SELECT user_query, response_text, retrieved_chunk_ids
                  FROM ai.ai_interactions WHERE id = :id
                """
            ),
            {"id": interaction_id},
        )
    ).one_or_none()
    if luot is None or not luot[1] or not luot[2]:
        return None
    doan = await session.execute(
        text("SELECT id, content FROM knowledge.knowledge_chunks WHERE id = ANY(:ids)"),
        {"ids": list(luot[2])},
    )
    theo_id = {ma: noi_dung for ma, noi_dung in doan.all()}
    cac_doan = [theo_id[ma] for ma in luot[2] if ma in theo_id]
    if not cac_doan:
        return None
    return NoiDungLuot(luot[0] or "", luot[1], cac_doan)


# ── UC041 — xoá dữ liệu cá nhân (ADR-0033) ───────────────────────────────────


@dataclass(frozen=True, slots=True)
class KetQuaXoaLuot:
    so_luot: int
    so_danh_gia: int
    so_goi_cong_cu: int


async def xoa_theo_hoi_thoai(
    session: AsyncSession, conversation_ids: Sequence[UUID]
) -> KetQuaXoaLuot:
    """Xoá CỨNG mọi lượt của các hội thoại đã cho — kể cả lượt ``SUMMARY`` (bản tóm tắt cũ cũng là
    dữ liệu cá nhân). ``ai_feedback`` và ``ai_tool_calls`` đi theo ``ON DELETE CASCADE`` (V204,
    V205); đếm TRƯỚC khi xoá để biên bản có số theo từng bảng.

    Khoá là ``conversation_id`` vì ``ai_interactions`` không có ``contact_id`` (liên làn, V204):
    danh sách hội thoại của khách do java-core gửi kèm — chỉ java-core biết khách nào có hội thoại
    nào. RLS chặn tenant khác: id hội thoại của tenant khác không khớp dòng nào.

    ``ai_tool_calls``: ``ai_app`` bị thu hồi DELETE (V206 — "không có đường nào xoá bằng chứng"),
    nhưng hành động xoá lan của khoá ngoại chạy bằng quyền chủ bảng, nên lan được. Nhóm MCP đã hoãn
    nên bảng đang rỗng; khi bật lại thì cân nhắc ẩn danh hoá ``arguments`` thay vì xoá (ADR-0033).
    """
    if not conversation_ids:
        return KetQuaXoaLuot(0, 0, 0)
    tham_so = {"ids": [UUID(str(c)) for c in conversation_ids]}
    dem = await session.execute(
        text(
            """
            SELECT (SELECT count(*) FROM ai.ai_feedback f
                      JOIN ai.ai_interactions i ON i.id = f.ai_interaction_id
                     WHERE i.conversation_id = ANY(:ids)),
                   (SELECT count(*) FROM ai.ai_tool_calls t
                      JOIN ai.ai_interactions i ON i.id = t.ai_interaction_id
                     WHERE i.conversation_id = ANY(:ids))
            """
        ),
        tham_so,
    )
    so_danh_gia, so_goi = dem.one()
    xoa = await session.execute(
        text("DELETE FROM ai.ai_interactions WHERE conversation_id = ANY(:ids)"), tham_so
    )
    return KetQuaXoaLuot(xoa.rowcount, so_danh_gia, so_goi)
