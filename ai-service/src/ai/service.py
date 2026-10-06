r"""FACADE DUY NHẤT của khối AI — §3.9.2.

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

Các phương thức của facade — bám theo 10 endpoint §2.5 và hai topic §2.6:
    answer_turn()      UC022/023/025/028   POST /v1/ai/chat     ĐÃ CÓ (UC022; RAG chưa nối)
    extract_signal()   UC029               POST /v1/ai/extract
    score_lead()       UC030               POST /v1/ai/lead-score
    index_document()   UC018/019           POST /v1/ai/kb/documents
    nap_tai_lieu()     UC019               (bất đồng bộ, từ crm.kb.document.uploaded) — Ngày 4–5
    quet_job_ket()     UC019               (bộ quét trong worker, ADR-0024) — Ngày 5
    tien_do_nap()      UC019               GET /v1/ai/kb/ingestion-jobs/{job_id} — Ngày 5
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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.config import get_settings
from src.ai.db.repositories import (
    chunk_repository,
    document_repository,
    processed_event_repository,
)
from src.ai.db.session import get_system_session, get_tenant_session
from src.ai.exceptions import (
    AiServiceError,
    DocumentNotFoundError,
    EmbeddingModelMismatchError,
    EmbeddingRejectedError,
    FileTooLargeError,
    ForbiddenFileUriError,
    IngestOwnershipLostError,
    IngestRetryExhaustedError,
    IngestStalledError,
    NoTextExtractedError,
    ParseFailedError,
    ParseTimeoutError,
    StoredFileNotFoundError,
)
from src.ai.inference.clients import (
    ClassifyClient,
    EmbedClient,
    KetQuaNhung,
    get_classify_client,
)
from src.ai.integrations import object_storage
from src.ai.orchestrator.turn import (
    KnowledgeAnswerer,
    LogTurnRecorder,
    PendingKnowledgeAnswerer,
    TurnRecorder,
    run_turn,
)
from src.ai.rag.ingest import tien_do
from src.ai.rag.ingest.chia_doan import Doan
from src.ai.rag.ingest.duong_ong import chia_doan_tu_khoi, trich_khoi_tu_s3
from src.ai.rag.ingest.luu_tru import kiem_uri_thuoc_tenant
from src.ai.rag.ingest.mime import nhan_dien_tep
from src.ai.rag.ingest.nhung import nhung_va_ghi_theo_lo
from src.ai.schemas import (
    ChatRequest,
    ChatResponse,
    IngestionJobProgress,
    IngestionStep,
    KbDocumentAccepted,
    KbDocumentCreate,
)

logger = logging.getLogger(__name__)


async def answer_turn(
    *,
    tenant_id: str,
    request: ChatRequest,
    classifier: ClassifyClient | None = None,
    answerer: KnowledgeAnswerer | None = None,
    recorder: TurnRecorder | None = None,
) -> ChatResponse:
    """Một lượt hội thoại: guardrails -> phân loại -> định tuyến -> trả lời -> ghi (UC022).

    ``tenant_id`` đến từ header đã xác thực (``api/deps.py``), không bao giờ từ ``request``.
    Ba phụ thuộc để trống thì lấy bản mặc định; test truyền bản giả vào.
    """
    settings = get_settings()
    return await run_turn(
        tenant_id=tenant_id,
        request=request,
        classifier=classifier or get_classify_client(),
        answerer=answerer or PendingKnowledgeAnswerer(),
        recorder=recorder or LogTurnRecorder(),
        fast_path_threshold=settings.fast_path_threshold,
        abstention_threshold=settings.router_abstention_threshold,
        classify_timeout_s=settings.classify_timeout_s,
        classify_retries=settings.classify_retries,
    )


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


# ── UC019 — nạp tài liệu: phân tích, chia đoạn, nhúng, lập chỉ mục (ADR-0024) ──

# Lỗi VĨNH VIỄN: thử lại bao nhiêu lần cũng ra cùng kết quả → tài liệu chuyển FAILED ngay, người
# dùng sửa tệp rồi tải lại. Mọi lỗi khác (StorageUnavailableError, EmbeddingUnavailableError, lỗi
# CSDL) là TẠM THỜI: tài liệu về lại PENDING và được thử lại, tới trần ``kb_so_luot_toi_da``. Gộp
# hai loại làm một là hoặc đẩy tệp tốt vào FAILED chỉ vì S3 chớp tắt, hoặc thử lại mãi một PDF scan.
#
# PARSE_TIMEOUT xếp vào vĩnh viễn: trần 120 s gấp hàng chục lần thời gian đo được cho một PDF
# 100 trang, nên quá trần gần như chắc chắn là tệp hỏng chứ không phải máy bận.
# EMBEDDING_MODEL_MISMATCH xếp vào vĩnh viễn: nạp tiếp là ghi vector của một không gian khác vào
# kho.
_LOI_VINH_VIEN = (
    NoTextExtractedError,
    ParseFailedError,
    ParseTimeoutError,
    StoredFileNotFoundError,
    ForbiddenFileUriError,
    EmbeddingRejectedError,
    EmbeddingModelMismatchError,
)


@dataclass(frozen=True, slots=True)
class SuKienNap:
    """Định danh sự kiện Kafka đã gây ra lượt nạp — khoá chống trùng của ``ai.processed_events``."""

    consumer_group: str
    event_id: int


@dataclass(frozen=True, slots=True)
class KetQuaNap:
    """Kết cục một lần gọi ``nap_tai_lieu``.

    ``READY``     xong, ``so_doan`` đoạn đã vào ``knowledge_chunks`` kèm vector.
    ``FAILED``    đã ghi ``FAILED`` + ``error_message``; ``loi`` là mã lỗi.
    ``THU_LAI``   lỗi tạm thời, tài liệu đã về ``PENDING`` — nơi gọi chờ rồi gọi lại (không kèm sự
                  kiện). ``loi`` là mã lỗi tạm thời.
    ``BO_QUA``    tài liệu không còn ``PENDING`` hoặc không thuộc tenant — không có việc gì làm.
    ``TRUNG``     sự kiện đã xử lý từ trước (``ai.processed_events``).
    ``MAT_QUYEN`` bộ quét đã trả tài liệu về hàng đợi giữa chừng; lượt này dừng, không ghi gì thêm.
    """

    trang_thai: Literal["READY", "FAILED", "THU_LAI", "BO_QUA", "TRUNG", "MAT_QUYEN"]
    lan: int | None = None
    so_doan: int = 0
    loi: str | None = None


SessionFactory = async_sessionmaker[AsyncSession] | None


async def nap_tai_lieu(
    tenant_id: str,
    document_id: UUID,
    *,
    embed: EmbedClient,
    su_kien: SuKienNap | None = None,
    factory: SessionFactory = None,
) -> KetQuaNap:
    """UC019 — một lượt nạp trọn vẹn:
    nhận việc → EXTRACTING → CHUNKING → EMBEDDING → INDEXING → READY.

    MỖI CHẶNG MỘT TRANSACTION (ADR-0024, phương án 2) — để SCR033 thấy được tiến độ, và để một
    tài liệu 3.000 đoạn không giữ một transaction mở hàng phút. Hệ quả phải trả, và cách trả:

    - Tiến trình chết giữa chừng để lại ``PROCESSING`` ⇒ bộ quét (``quet_job_ket``) nhặt lại.
    - Lượt bị bộ quét tước quyền mà vẫn chạy tiếp ⇒ mọi ghi đều kèm thẻ sở hữu ``attempt_count``;
      mất quyền thì dừng (``MAT_QUYEN``), không ghi đè lượt mới.
    - Đoạn dở dang của lượt trước ⇒ xoá ngay trong transaction nhận việc.

    ``su_kien`` có mặt khi lượt nạp do một bản tin Kafka gây ra: ghi ``ai.processed_events`` CÙNG
    transaction với bước nhận việc — sự kiện được đánh dấu xong đúng lúc tài liệu vào tay worker.
    Từ đó về sau, việc hoàn tất tài liệu thuộc về máy trạng thái của nó (và bộ quét), không thuộc
    offset Kafka nữa. Lượt thử lại sau ``THU_LAI`` và lượt do bộ quét gọi thì KHÔNG kèm sự kiện.

    Ngoại lệ thoát ra khỏi hàm này nghĩa là không ghi được cả trạng thái kết cục (thường là CSDL
    chết). Tài liệu có thể đang kẹt ``PROCESSING`` — bộ quét là lưới an toàn cho đúng ca đó.
    """
    settings = get_settings()

    # ── Nhận việc ────────────────────────────────────────────────────────────
    async with get_tenant_session(tenant_id, factory) as phien:
        if su_kien is not None and not await processed_event_repository.ghi_nhan(
            phien, su_kien.consumer_group, su_kien.event_id, document_id
        ):
            return KetQuaNap("TRUNG")
        tai_lieu = await document_repository.nhan_xu_ly(phien, document_id)
        if tai_lieu is None:
            return KetQuaNap("BO_QUA")
        await chunk_repository.xoa_theo_tai_lieu(phien, document_id)
    lan = tai_lieu.lan

    async def ghi_buoc(buoc: str, *, chunk_count: int | None = None) -> None:
        async with get_tenant_session(tenant_id, factory) as phien:
            await document_repository.danh_dau_buoc(
                phien, document_id, lan, buoc, chunk_count=chunk_count
            )

    async def ghi_lo(lo: Sequence[Doan], nhung: KetQuaNhung) -> None:
        async with get_tenant_session(tenant_id, factory) as phien:
            # Nhịp tim + thẻ sở hữu TRƯỚC khi ghi: mất quyền thì lô này không được vào kho.
            await document_repository.danh_dau_buoc(phien, document_id, lan, "EMBEDDING")
            await chunk_repository.them_lo(
                phien,
                document_id,
                lo,
                nhung.vectors,
                embedding_model=nhung.model_id,
                embedding_version=nhung.model_version,
            )

    try:
        # ── EXTRACTING ───────────────────────────────────────────────────────
        # Kiểm lại URI dù file_path do chính UC018 ghi sau khi đã kiểm: dòng trong CSDL có thể bị
        # sửa ngoài luồng (UC020, thao tác tay), và giá phải trả chỉ là một phép so chuỗi.
        key = kiem_uri_thuoc_tenant(tai_lieu.file_path, tenant_id, settings.s3_bucket)
        cac_khoi = await trich_khoi_tu_s3(
            settings.s3_bucket,
            key,
            tai_lieu.source_type,
            gioi_han_byte=settings.kb_max_file_bytes,
            timeout_s=settings.kb_parse_timeout_s,
        )

        # ── CHUNKING ─────────────────────────────────────────────────────────
        await ghi_buoc("CHUNKING")
        cac_doan = chia_doan_tu_khoi(cac_khoi, tai_lieu.source_type, settings.kb_chunk_tokens)
        del cac_khoi

        # ── EMBEDDING ────────────────────────────────────────────────────────
        await ghi_buoc("EMBEDDING", chunk_count=len(cac_doan))
        await nhung_va_ghi_theo_lo(cac_doan, embed, ghi_lo, co_lo=settings.kb_embed_batch)

        # ── INDEXING ─────────────────────────────────────────────────────────
        # Kiểm đếm trước khi công bố READY: đủ số đoạn, đoạn nào cũng có vector. Lệch nghĩa là có
        # lỗi mình chưa hiểu — coi là tạm thời, lượt sau nạp lại từ đầu.
        await ghi_buoc("INDEXING")
        async with get_tenant_session(tenant_id, factory) as phien:
            tong, co_vector = await chunk_repository.dem_doan_co_vector(phien, document_id)
            if tong != len(cac_doan) or co_vector != tong:
                raise RuntimeError(
                    f"Kiểm đếm hỏng: dự kiến {len(cac_doan)} đoạn, có {tong}, {co_vector} có vector"
                )
            await document_repository.hoan_tat(phien, document_id, lan, tong)

    except IngestOwnershipLostError:
        logger.warning(
            "Lượt %s mất quyền trên tài liệu %s — dừng, không ghi thêm", lan, document_id
        )
        return KetQuaNap("MAT_QUYEN", lan)

    except _LOI_VINH_VIEN as loi:
        if isinstance(loi, ForbiddenFileUriError):
            logger.warning("Tài liệu %s có file_path ngoài vùng tenant", document_id)
        if not await _ket_thuc_that_bai(tenant_id, document_id, lan, loi, factory):
            return KetQuaNap("MAT_QUYEN", lan)
        return KetQuaNap("FAILED", lan, loi=loi.code)

    except Exception as loi:  # noqa: BLE001 — mọi lỗi còn lại là TẠM THỜI, xem _LOI_VINH_VIEN
        ma = loi.code if isinstance(loi, AiServiceError) else "INTERNAL_ERROR"
        logger.warning(
            "Lỗi tạm thời ở lượt %s/%s, tài liệu %s: %s",
            lan, settings.kb_so_luot_toi_da, document_id, ma, exc_info=loi,
        )
        if lan >= settings.kb_so_luot_toi_da:
            # Câu hiển thị cho người dùng KHÔNG chứa str(loi): lỗi CSDL mang nguyên câu SQL và
            # tham số, lỗi kết nối mang địa chỉ nội bộ. Chi tiết đã vào log ở trên.
            het_luot = IngestRetryExhaustedError(
                f"{ma}: hạ tầng không phản hồi sau {lan} lượt thử — hãy tải lại tài liệu sau"
            )
            if not await _ket_thuc_that_bai(tenant_id, document_id, lan, het_luot, factory):
                return KetQuaNap("MAT_QUYEN", lan)
            return KetQuaNap("FAILED", lan, loi=het_luot.code)
        async with get_tenant_session(tenant_id, factory) as phien:
            if not await document_repository.tra_ve_hang_doi(phien, document_id, lan):
                return KetQuaNap("MAT_QUYEN", lan)
            await chunk_repository.xoa_theo_tai_lieu(phien, document_id)
        return KetQuaNap("THU_LAI", lan, loi=ma)

    return KetQuaNap("READY", lan, so_doan=tong)


async def _ket_thuc_that_bai(
    tenant_id: str, document_id: UUID, lan: int, loi: AiServiceError, factory: SessionFactory
) -> bool:
    """Ghi ``FAILED`` và dọn đoạn dở dang trong một transaction. ``False`` nếu đã mất quyền.

    Đoạn của tài liệu FAILED phải biến mất: để lại thì truy hồi (Ngày 6) có thể trả về nửa tài
    liệu hỏng nếu quên lọc theo trạng thái tài liệu.
    """
    async with get_tenant_session(tenant_id, factory) as phien:
        if not await document_repository.danh_dau_that_bai(phien, document_id, loi, lan=lan):
            return False
        await chunk_repository.xoa_theo_tai_lieu(phien, document_id)
    return True


# ── UC019 — bộ quét job kẹt (ADR-0024) ───────────────────────────────────────


@dataclass(frozen=True, slots=True)
class JobCanNapLai:
    """Tài liệu bộ quét đã trả về hàng đợi — worker phải gọi ``nap_tai_lieu`` cho nó."""

    tenant_id: str
    document_id: UUID


async def quet_job_ket(
    *, factory: SessionFactory = None, toi_da: int = 100
) -> list[JobCanNapLai]:
    """Tìm tài liệu kẹt ở MỌI tenant và xử lý từng cái trong phiên của đúng tenant đó.

    ``PROCESSING`` quá hạn nhịp tim — tiến trình đã chết giữa chừng:
        còn lượt (``attempt_count`` < trần) → ``PENDING``, dọn đoạn dở, trả về để nạp lại;
        hết lượt → ``FAILED`` ``INGEST_STALLED``. Một tệp làm chết worker sẽ làm chết mọi lượt —
        không có trần thì worker khởi động lại vô hạn.
    ``PENDING`` có ``attempt_count`` > 0 quá hạn — đã được trả về hàng đợi rồi tiến trình chết
        trước khi nhận lại: trả về để nạp lại.

    Tại sao KHÔNG phát lại sự kiện Kafka: sự kiện gốc đã được xác nhận offset (nó đã làm xong phần
    của nó — đưa tài liệu vào tay worker), và ``crm.kb.document.uploaded`` là topic của java-core.
    Worker gọi thẳng ``nap_tai_lieu`` cho các job trả về, qua cùng semaphore với luồng Kafka.
    """
    settings = get_settings()
    qua_han = settings.kb_job_ket_sau_s

    async with get_system_session(factory) as phien:
        cac_job = await document_repository.tim_job_ket(phien, qua_han, toi_da)

    can_nap_lai: list[JobCanNapLai] = []
    for job in cac_job:
        tenant = str(job.tenant_id)
        if job.status == "PENDING":
            can_nap_lai.append(JobCanNapLai(tenant, job.document_id))
            continue
        async with get_tenant_session(tenant, factory) as phien:
            moi = await document_repository.xu_ly_job_ket(
                phien,
                job.document_id,
                qua_han_s=qua_han,
                tran_luot=settings.kb_so_luot_toi_da,
                loi=IngestStalledError(
                    f"tiến trình nạp dừng giữa chừng {job.attempt_count} lần — tệp có thể làm "
                    "worker hết bộ nhớ; hãy kiểm tra tệp rồi tải lại"
                ),
            )
            if moi is None:
                continue
            await chunk_repository.xoa_theo_tai_lieu(phien, job.document_id)
        logger.warning(
            "Bộ quét: tài liệu %s kẹt PROCESSING (lượt %s) → %s",
            job.document_id, job.attempt_count, moi,
        )
        if moi == "PENDING":
            can_nap_lai.append(JobCanNapLai(tenant, job.document_id))
    return can_nap_lai


# ── UC019 — tiến độ nạp, SCR033 ──────────────────────────────────────────────


async def tien_do_nap(session: AsyncSession, job_id: UUID) -> IngestionJobProgress:
    """Sáu bước tiến độ của một job (``job_id`` = ``document_id``). 404 nếu không thấy qua RLS."""
    td = await document_repository.lay_tien_do(session, job_id)
    if td is None:
        raise DocumentNotFoundError(f"Không có job nạp {job_id}")

    ma_loi, cau_loi = None, None
    if td.status == "FAILED" and td.error_message:
        ma_loi, _, cau_loi = td.error_message.partition(": ")
        cau_loi = cau_loi or td.error_message

    # Mẫu số chỉ có từ chặng CHUNKING (chunk_count = số đoạn dự kiến); trước đó chưa biết.
    co_mau_so = td.status == "READY" or td.ingest_step in ("EMBEDDING", "INDEXING")
    tong = td.chunk_count if co_mau_so else None
    if td.status == "READY":
        phan_tram = 100.0
    elif tong:
        phan_tram = round(min(td.so_doan_da_ghi / tong, 1.0) * 100, 1)
    else:
        phan_tram = 0.0

    ket_thuc = td.indexed_at if td.status == "READY" else (
        td.updated_at if td.status == "FAILED" else None
    )
    thoi_gian = (
        int((ket_thuc - td.ingest_started_at).total_seconds() * 1000)
        if ket_thuc and td.ingest_started_at
        else None
    )

    return IngestionJobProgress(
        job_id=td.id,
        document_id=td.id,
        document_title=td.title,
        state=tien_do.buoc_hien_tai(td.status, td.ingest_step),
        status=td.status,
        attempt=td.attempt_count,
        steps=[
            IngestionStep(step=b, state=t)
            for b, t in tien_do.dung_cac_buoc(td.status, td.ingest_step)
        ],
        chunks_created=td.so_doan_da_ghi,
        chunks_total=tong,
        percent=phan_tram,
        error_code=ma_loi,
        error_message=cau_loi,
        duration_ms=thoi_gian,
        started_at=td.ingest_started_at,
        finished_at=ket_thuc,
        created_at=td.created_at,
        updated_at=td.updated_at,
    )
