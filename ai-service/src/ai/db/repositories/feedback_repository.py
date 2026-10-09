"""Đánh giá chất lượng một lượt trả lời — ``ai.ai_feedback`` (V204). UC027. [PRODUCTION]

MỘT CÂU LỆNH, BA RÀNG BUỘC
-------------------------
``INSERT … SELECT … FROM ai.ai_interactions WHERE id = :id … ON CONFLICT DO UPDATE``:

1. **Lượt phải thuộc tenant hiện tại.** Đây là chỗ dễ sai nhất của cả UC027: khoá ngoại
   ``ai_feedback → ai_interactions`` KHÔNG chịu RLS — Postgres kiểm khoá ngoại bằng quyền hệ thống
   và thấy MỌI dòng. ``INSERT … VALUES (:id …)`` thẳng thì tenant B gắn được đánh giá vào lượt của
   tenant A chỉ cần biết id (dòng mới mang tenant_id của B, nên WITH CHECK của RLS vẫn cho qua). Đi
   qua ``SELECT`` thì RLS lọc lượt của A ⇒ 0 dòng ⇒ 404 ``INTERACTION_NOT_FOUND``, không phân biệt
   được với "không tồn tại" — đúng ý: 403 là xác nhận cho kẻ dò rằng id đó có thật.
2. **Một phía một đánh giá** — chỉ mục duy nhất ``uq_feedback_rater`` (V204) trên biểu thức
   ``COALESCE(rater_user_id, 0…0)``. ``ON CONFLICT`` phải ghi đúng biểu thức đó để Postgres suy ra
   chỉ mục; ghi thiếu ``COALESCE`` thì hai đánh giá của khách (``rater_user_id`` NULL) không bao
   giờ "trùng" nhau vì NULL ≠ NULL.
3. **Đánh giá lại thì cập nhật, không báo lỗi** (UC027 luồng phụ 2.1 — ``DUPLICATE_FEEDBACK``
   chuyển thành cập nhật). ``xmax = 0`` cho biết dòng vừa chèn hay vừa cập nhật.

Hai CHECK của V204 (chê thì có lý do; nhân viên thì có mã người dùng) là lớp cuối — tầng ứng dụng
kiểm trước để trả mã lỗi có nghĩa thay vì 500.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class KetQuaGhiDanhGia:
    feedback_id: UUID
    tao_moi: bool


async def ghi_danh_gia(
    session: AsyncSession,
    *,
    interaction_id: UUID,
    rater_type: str,
    rater_user_id: UUID | None,
    rating: str,
    reason_code: str | None,
    comment: str | None,
    correction_text: str | None,
) -> KetQuaGhiDanhGia | None:
    """UPSERT một đánh giá. ``None`` = lượt không tồn tại hoặc thuộc tenant khác."""
    ket_qua = await session.execute(
        text(
            """
            INSERT INTO ai.ai_feedback (
                tenant_id, ai_interaction_id, rater_type, rater_user_id,
                rating, reason_code, comment, correction_text
            )
            SELECT ai.current_tenant(), i.id, :rater_type, :rater_user_id,
                   :rating, :reason_code, :comment, :correction_text
              FROM ai.ai_interactions i
             WHERE i.id = :interaction_id
            ON CONFLICT (ai_interaction_id, rater_type,
                         COALESCE(rater_user_id, '00000000-0000-0000-0000-000000000000'::uuid))
            DO UPDATE SET rating          = EXCLUDED.rating,
                          reason_code     = EXCLUDED.reason_code,
                          comment         = EXCLUDED.comment,
                          correction_text = EXCLUDED.correction_text
            RETURNING id, (xmax = 0)
            """
        ),
        {
            "interaction_id": interaction_id,
            "rater_type": rater_type,
            "rater_user_id": rater_user_id,
            "rating": rating,
            "reason_code": reason_code,
            "comment": comment,
            "correction_text": correction_text,
        },
    )
    dong = ket_qua.one_or_none()
    return None if dong is None else KetQuaGhiDanhGia(dong[0], bool(dong[1]))
