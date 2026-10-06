"""Tiện ích dùng chung cho test nạp tài liệu — làm phần việc của UC018 và đọc lại kết quả."""

import io
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text

from src.ai import service
from src.ai.db import session as db_session
from src.ai.db.repositories import document_repository
from src.ai.inference.clients import EmbedClient, MockEmbedClient
from tests.conftest import S3_BUCKET

MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"


async def tai_lieu_pending(factory, kho_s3, tenant: UUID, ten_tep: str, source_type: str,
                           du_lieu: bytes | None = None) -> UUID:
    """Làm đúng phần việc của UC018: object dưới key của tenant + dòng PENDING."""
    key = f"{tenant}/{uuid4()}/{ten_tep}"
    if du_lieu is None:
        du_lieu = (MAU / ten_tep).read_bytes()
    if du_lieu:  # b"" = cố ý KHÔNG đưa lên S3
        kho_s3.put_object(S3_BUCKET, key, io.BytesIO(du_lieu), len(du_lieu))
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return await document_repository.them_tai_lieu_pending(
            phien,
            title=f"{ten_tep} [{uuid4().hex[:8]}]",
            description=None,
            language="vi",
            source_type=source_type,
            file_name=ten_tep,
            file_path=f"s3://{S3_BUCKET}/{key}",
            mime_type="application/octet-stream",
            file_size_bytes=len(du_lieu),
            version=1,
            uploaded_by=None,
        )


async def nap(factory, tenant: UUID, doc: UUID, *, embed: EmbedClient | None = None,
              su_kien: service.SuKienNap | None = None) -> service.KetQuaNap:
    """Một lượt ``nap_tai_lieu`` như worker sẽ gọi — mỗi chặng tự mở phiên của nó."""
    return await service.nap_tai_lieu(
        str(tenant), doc, embed=embed or MockEmbedClient(1024), su_kien=su_kien, factory=factory
    )


async def doc_mot(factory, tenant: UUID, sql: str, **tham_so):
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return (await phien.execute(text(sql), tham_so)).one()


async def trang_thai(factory, tenant: UUID, doc: UUID) -> tuple:
    """(status, error_message, attempt_count, ingest_step) của tài liệu."""
    return tuple(await doc_mot(
        factory, tenant,
        "SELECT status, error_message, attempt_count, ingest_step"
        " FROM knowledge.knowledge_documents WHERE id = :id",
        id=doc,
    ))


async def cac_doan(factory, tenant: UUID, doc: UUID) -> list:
    """Các đoạn trong kho, theo chunk_index."""
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return (await phien.execute(
            text(
                "SELECT chunk_index, content, heading, page_number, embedding IS NOT NULL,"
                " embedding_model, content_segmented IS NOT NULL"
                " FROM knowledge.knowledge_chunks WHERE document_id = :id ORDER BY chunk_index"
            ),
            {"id": doc},
        )).all()
