"""Chống xử lý trùng sự kiện Kafka — ``ai.processed_events`` (V211, ADR-0024). [PRODUCTION]

Giao nhận ít nhất một lần nghĩa là nhận trùng là CHẮC CHẮN: pod chết sau khi xử lý nhưng trước
khi xác nhận offset, rebalance giữa chừng, java-core phát lại một dòng outbox. Bảng này biến "đã
xử lý sự kiện X chưa" thành một phép kiểm khoá chính.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def da_xu_ly(session: AsyncSession, consumer_group: str, event_id: int) -> bool:
    """Sự kiện đã được ghi nhận xong chưa — phép kiểm SỚM, chỉ để khỏi tốn một lượt LLM.

    KHÔNG thay được ``ghi_nhan``: hai bản sao cùng tới thì cả hai thấy "chưa". UC026 dùng nó vì
    tác động chính (PATCH sang java-core) không nằm chung transaction với bảng này được — xem
    ``service.summarize``. Bản sao lọt qua phép kiểm này chỉ làm tóm tắt + PATCH thêm một lần
    (luỹ đẳng), rồi ``ghi_nhan`` vẫn chỉ cho đúng một dòng.
    """
    ket_qua = await session.execute(
        text(
            "SELECT 1 FROM ai.processed_events"
            " WHERE consumer_group = :nhom AND event_id = :event_id"
        ),
        {"nhom": consumer_group, "event_id": event_id},
    )
    return ket_qua.first() is not None


async def ghi_nhan(
    session: AsyncSession, consumer_group: str, event_id: int, aggregate_id: UUID | None
) -> bool:
    """Đánh dấu sự kiện đã xử lý. ``False`` = đã có từ trước ⇒ nơi gọi BỎ QUA sự kiện.

    ``INSERT … ON CONFLICT DO NOTHING`` chứ không ``SELECT`` rồi ``INSERT``: hai bản sao của cùng
    sự kiện tới hai consumer cùng lúc thì cả hai ``SELECT`` đều thấy "chưa có" và cả hai xử lý.
    Một câu INSERT thì khoá chính quyết định — đúng một bên chèn được (1 dòng), bên kia chờ bên
    này commit rồi nhận 0 dòng. Không cần khoá nào ở tầng ứng dụng.

    Phải chạy CÙNG transaction với việc sự kiện gây ra (ở đây: nhận xử lý tài liệu). Commit riêng
    trước thì pod chết giữa hai bước là sự kiện bị đánh dấu xong mà việc chưa làm — mất việc.
    """
    ket_qua = await session.execute(
        text(
            """
            INSERT INTO ai.processed_events (consumer_group, event_id, tenant_id, aggregate_id)
            VALUES (:nhom, :event_id, ai.current_tenant(), :aggregate_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"nhom": consumer_group, "event_id": event_id, "aggregate_id": aggregate_id},
    )
    return ket_qua.rowcount == 1
