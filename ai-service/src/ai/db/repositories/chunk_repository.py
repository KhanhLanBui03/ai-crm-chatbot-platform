"""Ghi ``knowledge.knowledge_chunks`` — UC019 (2/2). [PRODUCTION]

Mọi hàm nhận một ``AsyncSession`` ĐÃ gắn tenant. ``tenant_id`` của dòng mới lấy từ
``ai.current_tenant()`` — không nhận làm tham số, nên không có đường nào ghi đoạn của tenant A
vào kho của tenant B (cùng lý do như ``document_repository.them_tai_lieu_pending``).

``content_segmented`` KHÔNG có trong câu INSERT: từ V210 nó là cột GENERATED, Postgres tự tính từ
``content`` — ghi tay vào sẽ bị từ chối.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.rag.ingest.chia_doan import Doan

_SQL_THEM_DOAN = text(
    """
    INSERT INTO knowledge.knowledge_chunks (
        tenant_id, document_id, chunk_index, content, token_count,
        embedding, embedding_model, embedding_version, page_number, heading
    ) VALUES (
        ai.current_tenant(), :document_id, :chunk_index, :content, :token_count,
        CAST(:embedding AS vector), :embedding_model, :embedding_version, :page_number, :heading
    )
    """
)


def _vector_sang_chuoi(vector: Sequence[float]) -> str:
    """Dạng văn bản ``[x1,x2,…]`` mà kiểu ``vector`` của pgvector nhận qua CAST.

    Không dùng adapter ``pgvector.psycopg``: nó phải đăng ký trên TỪNG kết nối của pool, quên một
    chỗ là lỗi kiểu dữ liệu chỉ lộ ra khi pool cấp đúng kết nối đó. 8 chữ số có nghĩa là đủ —
    pgvector lưu ``float4`` (~7 chữ số), in dài hơn chỉ làm phình câu lệnh.
    """
    return "[" + ",".join(f"{x:.8g}" for x in vector) + "]"


async def them_lo(
    session: AsyncSession,
    document_id: UUID,
    cac_doan: Sequence[Doan],
    vectors: Sequence[Sequence[float]],
    *,
    embedding_model: str,
    embedding_version: str,
) -> None:
    """Ghi một lô đoạn cùng vector của chúng — một câu lệnh, nhiều bộ tham số (executemany).

    ``embedding_model``/``embedding_version`` là danh tính do ``ai-embed`` trả về cùng lô vector,
    không phải giá trị cấu hình của phía gọi (bất biến 1 §3.4.2).
    """
    if len(cac_doan) != len(vectors):
        raise ValueError(f"{len(cac_doan)} đoạn nhưng {len(vectors)} vector")
    await session.execute(
        _SQL_THEM_DOAN,
        [
            {
                "document_id": document_id,
                "chunk_index": doan.chunk_index,
                "content": doan.content,
                "token_count": doan.token_count,
                "embedding": _vector_sang_chuoi(vector),
                "embedding_model": embedding_model,
                "embedding_version": embedding_version,
                "page_number": doan.page_number,
                "heading": doan.heading,
            }
            for doan, vector in zip(cac_doan, vectors, strict=True)
        ],
    )


async def xoa_theo_tai_lieu(session: AsyncSession, document_id: UUID) -> int:
    """Xoá mọi đoạn của một tài liệu — dọn phần dở dang của lượt trước. Trả số dòng đã xoá."""
    ket_qua = await session.execute(
        text("DELETE FROM knowledge.knowledge_chunks WHERE document_id = :id"),
        {"id": document_id},
    )
    return ket_qua.rowcount


async def dem_doan_co_vector(session: AsyncSession, document_id: UUID) -> tuple[int, int]:
    """``(tổng số đoạn, số đoạn có vector)`` của một tài liệu — phép kiểm của chặng INDEXING."""
    ket_qua = await session.execute(
        text(
            "SELECT count(*), count(embedding) FROM knowledge.knowledge_chunks"
            " WHERE document_id = :id"
        ),
        {"id": document_id},
    )
    tong, co_vector = ket_qua.one()
    return tong, co_vector
