"""Chống xử lý trùng sự kiện Kafka — ``ai.processed_events`` (V211, ADR-0021). [PRODUCTION]

Giao nhận ít nhất một lần nghĩa là nhận trùng là CHẮC CHẮN: pod chết sau khi xử lý nhưng trước
khi xác nhận offset, rebalance giữa chừng, java-core phát lại một dòng outbox. Bảng này biến "đã
xử lý sự kiện X chưa" thành một phép kiểm khoá chính.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
