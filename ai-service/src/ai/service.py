"""FACADE DUY NHẤT của khối AI — §3.9.2.

Đây là bề mặt duy nhất mà ``src/api/`` và ``src/worker/`` được phép gọi vào. Mọi
năng lực bên dưới (``rag/``, ``orchestrator/``, ``mcp_client/``, ``extraction/``,
``scoring/``, ``clustering/``) đều đi qua đây.

VÌ SAO CÓ FACADE — không phải để cho "gọn"
-------------------------------------------
``api/`` và ``worker/`` **không được import chéo nhau** (§3.9.1: một image, hai vai
trò độc lập). Nhưng cả hai đều cần đúng những năng lực AI giống nhau: một lượt chat
đến từ HTTP và một hội thoại đóng đến từ Kafka chạy qua phần lớn cùng một đường ống.

Facade là chỗ duy nhất giữ được cả hai điều đó cùng lúc. Hệ quả kiểm tra được bằng
máy: ``src/ai/`` **không bao giờ** import ``src.api`` hay ``src.worker``.

Lệnh kiểm phải neo vào ĐẦU DÒNG, nếu không nó tự khớp chính câu lệnh viết trong
docstring này và báo vi phạm giả::

    grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' src/ai/

Nhờ chiều phụ thuộc một hướng này, ``tests/eval/`` chạy lại đúng đường ống RAG mà
không cần dựng máy chủ HTTP.

CHIỀU PHỤ THUỘC
---------------
    api ──┐
          ├──► ai/service.py ──► rag · orchestrator · mcp_client · extraction · scoring
    worker┘                  └──► db · events · telemetry · inference · integrations

TODO: các phương thức của facade — bám theo 10 endpoint §2.5 và hai topic §2.6:
    answer_turn()      UC022/023/025/028   POST /v1/ai/chat
    extract_signal()   UC029               POST /v1/ai/extract
    score_lead()       UC030               POST /v1/ai/lead-score
    index_document()   UC018/019           POST /v1/ai/kb/documents
    phan_tich_tai_lieu() UC019             (bất đồng bộ, từ crm.kb.document.uploaded) — Ngày 4
    delete_document()  UC020               DELETE /v1/ai/kb/documents/{id}
    reindex_tenant()   UC020               POST /v1/ai/kb/reindex
    record_feedback()  UC027               POST /v1/ai/feedback
    set_mcp_config()   UC021               PUT /v1/ai/mcp/config
    forget_contact()   UC041               DELETE /v1/ai/privacy/contacts/{id}
    usage_summary()    UC006/039           GET /v1/ai/usage
    summarize()        UC026               (bất đồng bộ, từ crm.conversation.closed)
"""

import asyncio
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.config import get_settings
from src.ai.db.repositories import document_repository
from src.ai.exceptions import (
    FileTooLargeError,
    ForbiddenFileUriError,
    NoTextExtractedError,
    ParseFailedError,
    ParseTimeoutError,
    StoredFileNotFoundError,
)
from src.ai.integrations import object_storage
from src.ai.rag.ingest.chia_doan import Doan
from src.ai.rag.ingest.duong_ong import trich_doan_tu_s3
from src.ai.rag.ingest.luu_tru import kiem_uri_thuoc_tenant
from src.ai.rag.ingest.mime import nhan_dien_tep
from src.ai.schemas import KbDocumentAccepted, KbDocumentCreate

logger = logging.getLogger(__name__)


async def index_document(
    session: AsyncSession, tenant_id: str, yeu_cau: KbDocumentCreate
) -> KbDocumentAccepted:
    """UC018 — nhận tài liệu java-core đã ghi vào kho S3, ghi ``PENDING``, trả về cho 202.

    Kết thúc ngay khi tài liệu được nhận — KHÔNG phân tích cú pháp, không chờ lập chỉ mục
    (UC019 chạy nền). Vì vậy PDF scan cũng được nhận 202 ở đây; nó chỉ chuyển ``FAILED`` kèm
    ``PARSE_NO_TEXT_EXTRACTED`` khi parser chạy.

    Thứ tự bước là thứ tự rẻ → đắt, để tệp sai bị loại trước khi tốn tài nguyên:
    kiểm URI (thuần tính toán) → HEAD lấy dung lượng (413 mà không phải tải) → tải về tệp tạm
    và kiểm định dạng thật → chạm CSDL.

    Tải cả tệp (tối đa 20 MiB) chứ không chỉ vài KB đầu: nhận ra DOCX cần danh mục ZIP, mà
    danh mục đó nằm ở CUỐI tệp.
    """
    settings = get_settings()
    gioi_han = settings.kb_max_file_bytes

    key = kiem_uri_thuoc_tenant(yeu_cau.file_uri, tenant_id, settings.s3_bucket)

    # Thư viện S3 và I/O đĩa đều đồng bộ → đẩy sang luồng phụ, không chặn vòng lặp sự kiện.
    dung_luong = await asyncio.to_thread(object_storage.lay_dung_luong, settings.s3_bucket, key)
    if dung_luong > gioi_han:
        raise FileTooLargeError(f"Tệp {dung_luong} byte, vượt giới hạn {gioi_han} byte")

    with tempfile.TemporaryDirectory(prefix="kb-") as thu_muc:
        tep_tam = Path(thu_muc) / "tep"
        await asyncio.to_thread(object_storage.tai_ve, settings.s3_bucket, key, tep_tam, gioi_han)
        tep = await asyncio.to_thread(nhan_dien_tep, tep_tam, yeu_cau.file_name, gioi_han)

    version = await document_repository.tinh_version_ke_tiep(session, yeu_cau.title)
    document_id = await document_repository.them_tai_lieu_pending(
        session,
        title=yeu_cau.title,
        description=yeu_cau.description,
        language=yeu_cau.language,
        source_type=tep.source_type,
        file_name=yeu_cau.file_name,
        # Dựng lại URI từ bucket + key đã kiểm, không lưu nguyên văn chuỗi phía gọi gửi.
        file_path=f"s3://{settings.s3_bucket}/{key}",
        mime_type=tep.mime_type,
        file_size_bytes=tep.size_bytes,
        version=version,
        uploaded_by=yeu_cau.uploaded_by,
    )

    return KbDocumentAccepted(
        document_id=document_id,
        job_id=document_id,
        title=yeu_cau.title,
        version=version,
        source_type=tep.source_type,
        mime_type=tep.mime_type,
    )


# ── UC019 (1/2) — phân tích tài liệu ─────────────────────────────────────────

# Lỗi VĨNH VIỄN: thử lại bao nhiêu lần cũng ra cùng kết quả → tài liệu chuyển FAILED, người dùng
# sửa tệp rồi tải lại. Mọi lỗi khác (StorageUnavailableError, lỗi CSDL) là TẠM THỜI: để ném ra,
# transaction huỷ, tài liệu quay về PENDING và worker nhận lại sau (Ngày 5 — đẩy DLQ khi hết
# lượt thử). Gộp hai loại làm một là hoặc đẩy tệp tốt vào FAILED chỉ vì S3 chớp tắt, hoặc thử
# lại mãi một PDF scan.
#
# PARSE_TIMEOUT xếp vào vĩnh viễn: trần 120 s gấp hàng chục lần thời gian đo được cho một PDF
# 100 trang, nên quá trần gần như chắc chắn là tệp hỏng chứ không phải máy bận.
_LOI_VINH_VIEN = (
    NoTextExtractedError,
    ParseFailedError,
    ParseTimeoutError,
    StoredFileNotFoundError,
    ForbiddenFileUriError,
)


@dataclass(frozen=True, slots=True)
class KetQuaPhanTich:
    """Kết quả ``phan_tich_tai_lieu``.

    ``BO_QUA``: tài liệu không còn ``PENDING`` — lượt khác đã nhận, hoặc không thuộc tenant.
    ``FAILED``: đã ghi ``FAILED`` + ``error_message``; ``loi`` là mã lỗi.
    ``PROCESSING``: phân tích xong, ``doan`` chờ nhúng (Ngày 5).
    """

    trang_thai: Literal["BO_QUA", "FAILED", "PROCESSING"]
    doan: list[Doan] = field(default_factory=list)
    loi: str | None = None


async def phan_tich_tai_lieu(
    session: AsyncSession, tenant_id: str, document_id: UUID
) -> KetQuaPhanTich:
    """UC019 (1/2) — nhận một tài liệu ``PENDING``, tải về, phân tích, chuẩn hoá, chia đoạn.

    Lỗi vĩnh viễn KHÔNG ném ra mà trả ``FAILED``: nếu ném, ``get_tenant_session`` sẽ rollback
    transaction và mất luôn dòng ``FAILED`` vừa ghi — tài liệu quay về ``PENDING``, bị nhận
    lại và hỏng lại mãi. Lỗi tạm thời thì ném, CHÍNH VÌ muốn rollback đó.

    Ngày 4 dừng ở ``PROCESSING`` + danh sách đoạn trong bộ nhớ; Ngày 5 nhúng, ghi
    ``knowledge_chunks`` và chuyển ``READY`` trong cùng lượt.
    """
    settings = get_settings()

    tai_lieu = await document_repository.nhan_xu_ly(session, document_id)
    if tai_lieu is None:
        return KetQuaPhanTich("BO_QUA")

    try:
        # Kiểm lại dù file_path do chính UC018 ghi sau khi đã kiểm: dòng trong CSDL có thể bị
        # sửa ngoài luồng (UC020, thao tác tay), và giá phải trả chỉ là một phép so chuỗi.
        key = kiem_uri_thuoc_tenant(tai_lieu.file_path, tenant_id, settings.s3_bucket)
        cac_doan = await trich_doan_tu_s3(
            settings.s3_bucket,
            key,
            tai_lieu.source_type,
            gioi_han_byte=settings.kb_max_file_bytes,
            timeout_s=settings.kb_parse_timeout_s,
            tran_token=settings.kb_chunk_tokens,
        )
    except _LOI_VINH_VIEN as loi:
        if isinstance(loi, ForbiddenFileUriError):
            logger.warning("Tài liệu %s có file_path ngoài vùng tenant", document_id)
        await document_repository.danh_dau_that_bai(session, document_id, loi)
        return KetQuaPhanTich("FAILED", loi=loi.code)

    return KetQuaPhanTich("PROCESSING", doan=cac_doan)
