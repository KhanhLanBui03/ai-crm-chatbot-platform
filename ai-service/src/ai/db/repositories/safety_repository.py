"""Đọc cảnh báo an toàn phía AI — UC040 bước 8 (phần Track B). [PRODUCTION]

Hai nguồn, cả hai nằm trong schema ``ai`` của ai-service:

- ``ai.ai_interactions.safety_flag`` (V208) — guardrails gắn cờ khi phát hiện tiêm chỉ thị hay dò dữ liệu.
  Phát hiện KHÔNG chặn luồng: câu trả lời vẫn đi tiếp, cờ là dấu vết để quản trị viên xem lại.
- ``ai.ai_tool_calls`` với ``decision = 'BLOCKED'`` (V205) — lời gọi công cụ MCP bị chặn. Nhóm MCP đã hoãn
  (UC021/024/028) nên hiện không có dòng nào, nhưng giữ nguồn để hợp đồng không phải đổi khi có.

java-core gộp thêm nguồn thứ ba (``platform.audit_logs`` mức CRITICAL) — ai-service không có quyền trên
schema đó (ADR-0002).

Lọc ``tenant_id`` NGAY TRONG câu (cùng RLS của phiên): lớp chặn thứ hai, không phụ thuộc một mình RLS.
Bằng chứng trả ra là trích đoạn NGẮN của câu hỏi đã che PII ở tầng ghi — không trả nguyên văn nội dung tấn
công (hợp đồng ``SuKienAnToan.evidence``).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Đủ để quản trị viên nhận ra kiểu tấn công, không đủ để chép lại nguyên câu tấn công
DO_DAI_TRICH = 40


@dataclass(frozen=True, slots=True)
class DongAnToan:
    id: UUID
    nguon: str  # INTERACTION | TOOL_CALL
    loai: str
    conversation_id: UUID | None
    interaction_id: UUID | None
    nhanh: str | None
    tu_choi: str | None
    chuyen_giao: bool
    trich: str | None
    chi_tiet: str | None
    luc: datetime


async def cac_su_kien(
    session: AsyncSession, *, tenant_id: str, tu: datetime, den: datetime, gioi_han: int
) -> list[DongAnToan]:
    """Cảnh báo trong khoảng ``[tu, den)``, mới nhất trước, tối đa ``gioi_han`` dòng mỗi nguồn."""
    co = await session.execute(
        text(
            """
            SELECT id, safety_flag, conversation_id, branch, refusal_reason, is_handoff,
                   left(user_query, :trich) AS trich, created_at
              FROM ai.ai_interactions
             WHERE tenant_id = CAST(:t AS uuid) AND safety_flag IS NOT NULL
               AND created_at >= :tu AND created_at < :den
             ORDER BY created_at DESC
             LIMIT :lim
            """
        ),
        {"t": tenant_id, "tu": tu, "den": den, "lim": gioi_han, "trich": DO_DAI_TRICH},
    )
    ket_qua = [
        DongAnToan(
            id=r.id, nguon="INTERACTION", loai=r.safety_flag, conversation_id=r.conversation_id,
            interaction_id=r.id, nhanh=r.branch, tu_choi=r.refusal_reason, chuyen_giao=bool(r.is_handoff),
            trich=r.trich, chi_tiet=None, luc=r.created_at,
        )
        for r in co.mappings().all()
    ]
    chan = await session.execute(
        text(
            """
            SELECT tc.id, tc.ai_interaction_id, tc.tool_name, tc.block_reason, tc.created_at,
                   i.conversation_id
              FROM ai.ai_tool_calls tc
              JOIN ai.ai_interactions i ON i.id = tc.ai_interaction_id AND i.tenant_id = tc.tenant_id
             WHERE tc.tenant_id = CAST(:t AS uuid) AND tc.decision = 'BLOCKED'
               AND tc.created_at >= :tu AND tc.created_at < :den
             ORDER BY tc.created_at DESC
             LIMIT :lim
            """
        ),
        {"t": tenant_id, "tu": tu, "den": den, "lim": gioi_han},
    )
    ket_qua += [
        DongAnToan(
            id=r.id, nguon="TOOL_CALL", loai="TOOL_CALL_BLOCKED", conversation_id=r.conversation_id,
            interaction_id=r.ai_interaction_id, nhanh="TOOL_CALL", tu_choi=None, chuyen_giao=False,
            trich=None, chi_tiet=f"{r.tool_name}: {r.block_reason}", luc=r.created_at,
        )
        for r in chan.mappings().all()
    ]
    ket_qua.sort(key=lambda d: d.luc, reverse=True)
    return ket_qua
