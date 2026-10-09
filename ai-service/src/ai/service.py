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
    answer_turn()      UC022/023/025/028   POST /v1/ai/chat     ĐÃ CÓ (UC022 + UC023 + UC025)
    extract_signal()   UC029               POST /v1/ai/extract
    score_lead()       UC030               POST /v1/ai/lead-score
    index_document()   UC018/019           POST /v1/ai/kb/documents
    nap_tai_lieu()     UC019               (bất đồng bộ, từ crm.kb.document.uploaded) — Ngày 4–5
    quet_job_ket()     UC019               (bộ quét trong worker, ADR-0024) — Ngày 5
    tien_do_nap()      UC019               GET /v1/ai/kb/ingestion-jobs/{job_id} — Ngày 5
    list_documents()   UC020               GET /v1/documents — Ngày 11
    get_document()     UC020               GET /v1/documents/{id} — Ngày 11
    list_chunks()      UC020               GET /v1/documents/{id}/chunks — Ngày 11
    update_document_metadata()  UC020      PATCH /v1/documents/{id} — Ngày 11
    reindex_document() UC020               POST /v1/documents/{id}/reindex — Ngày 11 (ADR-0031)
    delete_document()  UC020               DELETE /v1/documents/{id} · /v1/ai/kb/documents/{id}
    reindex_tenant()   UC020               POST /v1/ai/kb/reindex — Ngày 11
    record_feedback()  UC027               POST /v1/ai/feedback — Ngày 10
    knowledge_gaps()   UC025               GET /v1/knowledge-gaps — Ngày 10
    quality_summary()  UC027               GET /v1/ai/quality — Ngày 10
    cham_tu_dong_lo()  UC027               (bộ chấm tự động trong worker, mẫu 5%) — Ngày 10
    set_mcp_config()   UC021               PUT /v1/ai/mcp/config
    forget_contact()   UC041               DELETE /v1/ai/privacy/contacts/{id} — Ngày 12
    usage_summary()    UC006/039           GET /v1/ai/usage
    summarize()        UC026               (bất đồng bộ, từ crm.conversation.closed) — Ngày 12
    summarize_messages() UC026             POST /v1/ai/summarize (MANUAL) — Ngày 12
"""

import asyncio
import logging
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.config import get_settings
from src.ai.db.repositories import (
    chunk_repository,
    document_repository,
    feedback_repository,
    interaction_repository,
    processed_event_repository,
)
from src.ai.db.session import get_system_session, get_tenant_session
from src.ai.exceptions import (
    AiServiceError,
    ConversationTooShortError,
    DocumentArchivedError,
    DocumentBusyError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    EmbeddingModelMismatchError,
    EmbeddingRejectedError,
    FeedbackInteractionMissingError,
    FeedbackReasonRequiredError,
    FileTooLargeError,
    ForbiddenFileUriError,
    IngestOwnershipLostError,
    IngestRetryExhaustedError,
    IngestStalledError,
    InteractionNotFoundError,
    InvalidMetadataError,
    InvalidRaterError,
    NoTextExtractedError,
    ParseFailedError,
    ParseTimeoutError,
    StorageUnavailableError,
    StoredFileNotFoundError,
    SummarySchemaInvalidError,
)
from src.ai.inference.clients import (
    ClassifyClient,
    EmbedClient,
    KetQuaNhung,
    get_classify_client,
    get_rerank_client,
    tao_embed_client,
)
from src.ai.integrations import object_storage
from src.ai.integrations.java_core import (
    BanGhiTomTat,
    JavaCoreClient,
    TinNhanHoiThoai,
    tao_java_core_client,
)
from src.ai.integrations.llm import (
    CircuitBreaker,
    LLMChiuLoi,
    MockLLMClient,
    OpenAICompatLLMClient,
    tao_llm_chiu_loi,
    tao_llm_client,
)
from src.ai.orchestrator.ghi_luot import DbTurnRecorder
from src.ai.orchestrator.turn import (
    KnowledgeAnswerer,
    TurnRecorder,
    run_turn,
)
from src.ai.rag.answerer import RagAnswerer
from src.ai.rag.chuan_hoa import normalize_vi
from src.ai.rag.danh_gia.cham_tu_dong import cham
from src.ai.rag.generate import tom_tat
from src.ai.rag.ingest import tien_do
from src.ai.rag.ingest.chia_doan import Doan
from src.ai.rag.ingest.duong_ong import chia_doan_tu_khoi, trich_khoi_tu_s3
from src.ai.rag.ingest.luu_tru import kiem_uri_thuoc_tenant
from src.ai.rag.ingest.mime import nhan_dien_tep
from src.ai.rag.ingest.nhung import nhung_va_ghi_theo_lo
from src.ai.rag.tsquery import build_tsquery
from src.ai.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkItem,
    ChunkPage,
    DanhGiaPhia,
    DocumentDeleted,
    DocumentDetail,
    DocumentMetadataUpdate,
    DocumentPage,
    ErasureItem,
    ErasureResult,
    FeedbackRecorded,
    FeedbackRequest,
    IngestionJobProgress,
    IngestionStep,
    KbDocumentAccepted,
    KbDocumentCreate,
    KnowledgeGapItem,
    KnowledgeGapPage,
    QualitySummary,
    ReindexAccepted,
    ReindexTenantAccepted,
    SummarizeRequest,
    SummarizeResponse,
    TyLe,
)
from src.ai.telemetry.metrics import auto_eval, privacy_erasures, summaries

logger = logging.getLogger(__name__)


# ── UC023 — nhánh trả lời từ tri thức ────────────────────────────────────────

# MỘT RagAnswerer cho mỗi event loop, sống suốt vòng đời tiến trình. Không tạo mới mỗi lượt vì hai
# lẽ: circuit breaker phải NHỚ được các lượt hỏng trước (tạo mới là mạch không bao giờ mở), và
# httpx client giữ kết nối tới ai-embed + nhà cung cấp LLM (tạo mới tốn ~200 ms bắt tay TLS).
# Gắn theo loop như ``inference/clients._http``: kết nối httpx không dùng được sang loop khác.
_TRA_LOI: dict[int, RagAnswerer] = {}


def _rag_answerer() -> RagAnswerer:
    loop = id(asyncio.get_running_loop())
    tra_loi = _TRA_LOI.get(loop)
    if tra_loi is None:
        settings = get_settings()
        tra_loi = RagAnswerer(
            embed=tao_embed_client(settings),
            llm=tao_llm_chiu_loi(settings),
            settings=settings,
            rerank=get_rerank_client() if settings.rerank_enabled else None,
        )
        _TRA_LOI[loop] = tra_loi
    return tra_loi


async def khoi_dong_tra_loi() -> None:
    """Gọi trong lifespan: dựng client ngay lúc khởi động để cấu hình sai (thiếu ``LLM_API_KEY``
    khi ``LLM_MODE=remote``) làm pod không lên, thay vì nổ ở lượt chat đầu tiên.

    Làm nóng bộ tách từ pyvi luôn: lần tách đầu tiên nạp mô hình CRF mất ~1,6 s (đo 08/10) — để
    nguyên thì lượt chat đầu tiên sau mỗi lần khởi động pod chịu trọn khoản đó.
    """
    _rag_answerer()
    await asyncio.to_thread(build_tsquery, "khởi động")


async def dong_tra_loi() -> None:
    """Gọi trong lifespan lúc tắt — đóng kết nối tới ai-embed và nhà cung cấp LLM."""
    cac_tra_loi = list(_TRA_LOI.values())
    _TRA_LOI.clear()
    for tra_loi in cac_tra_loi:
        await tra_loi.aclose()


def _ghi_luot() -> TurnRecorder:
    """Recorder mặc định — ghi ``ai.ai_interactions`` (Ngày 10). Test HTTP thay bằng bản giả."""
    return DbTurnRecorder()


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
        answerer=answerer or _rag_answerer(),
        recorder=recorder or _ghi_luot(),
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


# ── UC027 — đánh giá chất lượng ──────────────────────────────────────────────

_DANH_GIA = {1: "POSITIVE", -1: "NEGATIVE"}


async def record_feedback(
    session: AsyncSession, yeu_cau: FeedbackRequest, interaction_id: UUID | None = None
) -> FeedbackRecorded:
    """Ghi (hoặc cập nhật) đánh giá của một phía cho một lượt — UC027 bước 5.

    ``interaction_id`` từ đường dẫn (``/v1/ai-interactions/{id}/feedback``) hoặc từ body
    (``/v1/ai/feedback``). Có cả hai mà khác nhau thì từ chối — không đoán bên nào đúng.

    Thứ tự kiểm: ràng buộc chéo trường (rẻ, không chạm CSDL) → ghi. Ràng buộc "lượt thuộc tenant"
    nằm TRONG câu ghi (``feedback_repository``) — không ``SELECT`` trước rồi ``INSERT`` sau.
    """
    ma_luot = interaction_id or yeu_cau.interaction_id
    if ma_luot is None or (
        interaction_id and yeu_cau.interaction_id and interaction_id != yeu_cau.interaction_id
    ):
        raise FeedbackInteractionMissingError("Cần đúng một interaction_id cho đánh giá")
    danh_gia = _DANH_GIA[yeu_cau.rating]
    if danh_gia == "NEGATIVE" and yeu_cau.reason_code is None:
        raise FeedbackReasonRequiredError("Đánh giá tiêu cực phải chọn một trong bốn lý do")
    if danh_gia == "POSITIVE" and yeu_cau.reason_code is not None:
        raise FeedbackInteractionMissingError("Đánh giá tích cực không kèm lý do chê")
    if yeu_cau.rater_type == "AGENT" and yeu_cau.rater_user_id is None:
        raise InvalidRaterError("Đánh giá của nhân viên phải có rater_user_id")
    if yeu_cau.rater_type == "CUSTOMER" and (
        yeu_cau.rater_user_id is not None or yeu_cau.corrected_answer is not None
    ):
        raise InvalidRaterError("Đánh giá của khách không kèm rater_user_id hay câu trả lời sửa")

    ket_qua = await feedback_repository.ghi_danh_gia(
        session,
        interaction_id=ma_luot,
        rater_type=yeu_cau.rater_type,
        rater_user_id=yeu_cau.rater_user_id,
        rating=danh_gia,
        reason_code=yeu_cau.reason_code,
        comment=yeu_cau.comment,
        correction_text=yeu_cau.corrected_answer,
    )
    if ket_qua is None:
        raise InteractionNotFoundError(f"Không có lượt xử lý {ma_luot}")
    return FeedbackRecorded(
        message="Đã ghi nhận đánh giá" if ket_qua.tao_moi else "Đã cập nhật đánh giá",
        feedback_id=ket_qua.feedback_id,
        created=ket_qua.tao_moi,
    )


def _ty_le(tu_so: int, mau_so: int) -> TyLe:
    return TyLe(tu_so=tu_so, mau_so=mau_so, gia_tri=round(tu_so / mau_so, 4) if mau_so else None)


async def quality_summary(session: AsyncSession, tu: datetime, den: datetime) -> QualitySummary:
    """Bảy tín hiệu chất lượng trong ``[tu, den)`` — UC027 bước 7, nguồn cho UC039.

    Mỗi tỉ lệ trả kèm tử số và mẫu số. Tỉ lệ đánh giá tích cực chia cho SỐ LƯỢT CÓ ĐÁNH GIÁ từ
    phía đó, không chia cho tổng số lượt: chia cho tổng lượt thì con số bị kéo về 0 theo tỉ lệ
    người chịu bấm nút — thứ đó đo mức sẵn lòng bấm của khách, không đo chất lượng câu trả lời.
    """
    t = await interaction_repository.tin_hieu_luot(session, tu, den)
    phia = await interaction_repository.danh_gia_theo_phia(session, tu, den)
    return QualitySummary(
        tu=tu,
        den=den,
        so_luot=t.so_luot,
        so_luot_loi=t.so_loi,
        ty_le_tu_choi=_ty_le(t.so_tu_choi, t.so_luot),
        ty_le_suy_giam=_ty_le(t.so_suy_giam, t.so_luot),
        ty_le_chuyen_giao=_ty_le(t.so_chuyen_giao, t.so_luot),
        do_phu_trich_dan=_ty_le(t.so_rag_co_trich_dan, t.so_rag_tra_loi),
        ty_le_khong_goi_llm=_ty_le(t.so_khong_goi_llm, t.so_luot),
        groundedness_trung_binh=t.groundedness_tb,
        tu_choi_theo_ly_do=t.tu_choi_theo_ly_do,
        danh_gia=[
            DanhGiaPhia(
                rater_type=p.rater_type,
                ty_le_tich_cuc=_ty_le(p.so_tich_cuc, p.so_danh_gia),
                che_theo_ly_do=p.che_theo_ly_do,
            )
            for p in phia
        ],
    )


# ── UC025 — khoảng trống tri thức ────────────────────────────────────────────


async def knowledge_gaps(
    session: AsyncSession,
    tenant_id: str,
    *,
    gap_type: str | None = None,
    page: int = 0,
    size: int = 20,
    so_ngay: int = 30,
) -> KnowledgeGapPage:
    """Danh sách khoảng trống — UC025 bước 8. Truy vấn gộp, không bảng riêng (đặc tả UC025).

    ``tenant_id`` chỉ để dựng ``id`` tất định; việc lọc theo tenant là của RLS trong ``session``.
    """
    cac_dong, tong = await interaction_repository.khoang_trong_tri_thuc(
        session, so_ngay=so_ngay, gap_type=gap_type, gioi_han=size, bo_qua=page * size
    )
    return KnowledgeGapPage(
        items=[
            KnowledgeGapItem(
                id=uuid5(NAMESPACE_URL, f"knowledge-gap:{tenant_id}:{d.gap_type}:{d.khoa}"),
                query_text=d.query_text,
                gap_type=d.gap_type,
                unanswered_count=d.unanswered_count,
                distinct_conversation_count=d.distinct_conversation_count,
                first_occurred_at=d.first_occurred_at,
                last_occurred_at=d.last_occurred_at,
            )
            for d in cac_dong
        ],
        total=tong,
        page=page,
        size=size,
    )


# ── UC027 — bộ chấm tự động (worker) ─────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class KetQuaChamLo:
    so_ung_vien: int
    so_ghi: int
    so_khong_chac: int
    so_bo_qua: int
    # Mốc ``tu`` cho lần quét sau — xem ``cham_tu_dong_lo``.
    moc_tiep: datetime


def tao_giam_khao() -> LLMChiuLoi:
    """LLM giám khảo — mạch RIÊNG với LLM trả lời khách: giám khảo làm mở mạch thì khách không
    phải nhận câu suy giảm vì nó. Hạn chót rộng — chạy nền, không ai chờ."""
    s = get_settings()
    return LLMChiuLoi(
        tao_llm_client(s),
        CircuitBreaker(
            nguong_hong=s.llm_breaker_nguong_hong, thoi_gian_mo_s=s.llm_breaker_thoi_gian_mo_s
        ),
        han_chot_s=s.cham_tu_dong_han_chot_s,
    )


async def cham_tu_dong_lo(
    giam_khao: LLMChiuLoi, *, tu: datetime, factory: SessionFactory = None
) -> KetQuaChamLo:
    """Chấm mẫu 5% các lượt RAG đã trả lời từ ``tu`` tới nay — UC027 bước 6.

    Trả ``moc_tiep`` để worker dùng làm ``tu`` lần sau, nên mỗi lượt chỉ được XÉT một lần — lượt
    giám khảo không chắc (không ghi gì) không bị chấm lại mỗi chu kỳ và đốt hạn mức LLM:

    - lô CHƯA đầy ⇒ đã xét hết tới lúc quét ⇒ mốc = giờ CSDL lúc quét;
    - lô ĐẦY (đủ ``cham_tu_dong_toi_da``) ⇒ còn ứng viên phía sau ⇒ mốc = ``created_at`` của lượt
      cuối trong lô. Dời thẳng tới "bây giờ" là bỏ rơi vĩnh viễn phần vượt trần.
    """
    s = get_settings()
    async with get_system_session(factory) as phien:
        cac_luot, luc_quet = await interaction_repository.tim_luot_can_cham(
            phien, tu, s.cham_tu_dong_ty_le, s.cham_tu_dong_toi_da
        )
    moc_tiep = cac_luot[-1].created_at if len(cac_luot) >= s.cham_tu_dong_toi_da else luc_quet
    so_ghi = so_khong_chac = so_bo_qua = 0
    for luot in cac_luot:
        tenant = str(luot.tenant_id)
        async with get_tenant_session(tenant, factory) as phien:
            noi_dung = await interaction_repository.doc_luot_de_cham(phien, luot.interaction_id)
        if noi_dung is None:
            so_bo_qua += 1
            auto_eval.labels(outcome="BO_QUA").inc()
            continue
        ket_qua = await cham(giam_khao, noi_dung)
        if ket_qua is None or ket_qua.do_chac < s.cham_tu_dong_nguong_chac:
            so_khong_chac += 1
            auto_eval.labels(outcome="KHONG_CHAC").inc()
            continue
        async with get_tenant_session(tenant, factory) as phien:
            await feedback_repository.ghi_danh_gia(
                phien,
                interaction_id=luot.interaction_id,
                rater_type="AUTO_EVAL",
                rater_user_id=None,
                rating=ket_qua.rating,
                reason_code=ket_qua.reason_code,
                comment=f"[{ket_qua.model} · chắc {ket_qua.do_chac:.2f}] {ket_qua.giai_thich}",
                correction_text=None,
            )
        so_ghi += 1
        auto_eval.labels(outcome="GHI").inc()
    if cac_luot:
        logger.info(
            "Bộ chấm tự động: %d ứng viên — ghi %d, không chắc %d, bỏ qua %d",
            len(cac_luot), so_ghi, so_khong_chac, so_bo_qua,
        )
    return KetQuaChamLo(len(cac_luot), so_ghi, so_khong_chac, so_bo_qua, moc_tiep)


def bay_gio() -> datetime:
    """Đồng hồ của worker — một chỗ để test thay."""
    return datetime.now(UTC)


# ── UC020 — quản lý kho tri thức (ADR-0031) ──────────────────────────────────
#
# Mọi thao tác ghi khoá dòng tài liệu (``FOR UPDATE``) rồi mới kiểm trạng thái, trong CÙNG
# transaction của request (``SessionDep``): một lượt nạp không chen được vào giữa lúc kiểm "không
# bận" và lúc ghi. Ba thao tác ghi để lại một dòng log ``kiem_toan_kho`` — nhật ký kiểm toán thật
# (``platform.audit_logs``, đặc tả UC020 bước 8) là của java-core: ai-service không ghi schema của
# Track A.

_DANG_NAP = ("PENDING", "PROCESSING")


def _tai_lieu_ra(t: document_repository.TaiLieu) -> DocumentDetail:
    return DocumentDetail(
        id=t.id, title=t.title, status=t.status, source_type=t.source_type,
        uploaded_by=t.uploaded_by, chunk_count=t.chunk_count, created_at=t.created_at,
        description=t.description, language=t.language, file_name=t.file_name,
        mime_type=t.mime_type, file_size_bytes=t.file_size_bytes, version=t.version,
        error_message=t.error_message, indexed_at=t.indexed_at, updated_at=t.updated_at,
        replaces_document_id=t.replaces_document_id, reindex_document_id=t.reindex_document_id,
        contact_id=t.contact_id,
    )


async def _lay_hoac_404(
    session: AsyncSession, document_id: UUID, *, khoa: bool = False
) -> document_repository.TaiLieu:
    t = await document_repository.lay_tai_lieu(session, document_id, khoa=khoa)
    if t is None:
        raise DocumentNotFoundError(f"Không có tài liệu {document_id}")
    return t


def _kiem_toan(thao_tac: str, document_id: UUID, **chi_tiet) -> None:
    logger.info(
        "kiem_toan_kho thao_tac=%s tai_lieu=%s %s",
        thao_tac, document_id, " ".join(f"{k}={v}" for k, v in chi_tiet.items()),
    )


async def list_documents(
    session: AsyncSession,
    *,
    keyword: str | None,
    status: str | None,
    source_type: str | None,
    page: int,
    size: int,
) -> DocumentPage:
    """SCR030. Từ khoá qua ``normalize_vi`` — CÙNG hàm chuẩn hoá lúc nạp (kế hoạch Ngày 11: dùng
    lại, không viết hàm thứ hai); bỏ dấu + viết thường do ``knowledge.f_unaccent`` làm trong SQL."""
    tu_khoa = normalize_vi(keyword).strip() if keyword else None
    cac, tong = await document_repository.danh_sach(
        session, tu_khoa=tu_khoa or None, status=status, source_type=source_type,
        gioi_han=size, bo_qua=page * size,
    )
    return DocumentPage(items=[_tai_lieu_ra(t) for t in cac], total=tong, page=page, size=size)


async def get_document(session: AsyncSession, document_id: UUID) -> DocumentDetail:
    return _tai_lieu_ra(await _lay_hoac_404(session, document_id))


async def list_chunks(
    session: AsyncSession, document_id: UUID, *, page: int, size: int
) -> ChunkPage:
    await _lay_hoac_404(session, document_id)
    cac, tong = await chunk_repository.danh_sach_doan(session, document_id, size, page * size)
    return ChunkPage(
        items=[
            ChunkItem(
                chunk_id=d.id, chunk_index=d.chunk_index, content=d.content, heading=d.heading,
                page_number=d.page_number, token_count=d.token_count,
                embedding_model=d.embedding_model, embedding_version=d.embedding_version,
                has_vector=d.co_vector,
            )
            for d in cac
        ],
        total=tong, page=page, size=size,
    )


async def update_document_metadata(
    session: AsyncSession, document_id: UUID, yeu_cau: DocumentMetadataUpdate
) -> DocumentDetail:
    """Sửa ``title``/``description``/``contact_id``. KHÔNG đụng ``knowledge_chunks`` — chỉ mục
    vector giữ nguyên. ``contact_id`` (V214) gắn tài liệu với khách để UC041 xoá được.

    Chặn khi đang có lượt nạp lại: bản bóng đã chép tiêu đề cũ, sửa bản cũ lúc này thì tới khi đổi
    bản, tiêu đề mới biến mất mà không ai biết vì sao.
    """
    t = await _lay_hoac_404(session, document_id, khoa=True)
    if t.status == "ARCHIVED":
        raise DocumentArchivedError(f"Tài liệu {document_id} đã gỡ khỏi chỉ mục")
    if t.reindex_document_id is not None:
        raise DocumentBusyError(f"Tài liệu {document_id} đang được nạp lại")
    thay_doi = {c: getattr(yeu_cau, c) for c in yeu_cau.model_fields_set}
    try:
        await document_repository.cap_nhat_sieu_du_lieu(session, document_id, thay_doi)
    except IntegrityError as loi:
        if "uq_doc_title_version" in str(loi.orig):
            raise InvalidMetadataError(
                f"Đã có tài liệu khác tên '{thay_doi.get('title')}' ở version {t.version}"
            ) from None
        raise
    _kiem_toan("SUA", document_id, truong=",".join(sorted(thay_doi)))
    return _tai_lieu_ra(await _lay_hoac_404(session, document_id))


async def reindex_document(session: AsyncSession, document_id: UUID) -> ReindexAccepted:
    """Nạp lại một tài liệu bằng bản bóng (ADR-0031). Bộ quét nhặt bản bóng trong ≤ 1 chu kỳ."""
    t = await _lay_hoac_404(session, document_id, khoa=True)
    if t.status in _DANG_NAP or t.reindex_document_id is not None:
        raise DocumentBusyError(f"Tài liệu {document_id} đang được nạp")
    if t.status != "READY":
        raise DocumentNotReadyError(
            f"Chỉ nạp lại tài liệu READY; tài liệu đang {t.status} — hãy tải lên lại"
        )
    try:
        moi, version = await document_repository.tao_ban_bong(session, t)
    except IntegrityError as loi:
        if "uq_doc_mot_luot_nap_lai" in str(loi.orig):
            raise DocumentBusyError(f"Tài liệu {document_id} đang được nạp lại") from None
        raise
    _kiem_toan("NAP_LAI", document_id, ban_bong=moi, version=version)
    return ReindexAccepted(
        message="Đã xếp hàng nạp lại — bản cũ vẫn phục vụ tới khi bản mới nạp xong",
        document_id=document_id, job_id=moi, version=version,
    )


async def reindex_tenant(session: AsyncSession, tenant_id: str) -> ReindexTenantAccepted:
    """Nạp lại toàn kho của tenant (đổi mô hình nhúng — UC020 luồng phụ 6.1): một bản bóng cho mỗi
    tài liệu ``READY`` chưa có lượt nạp lại đang chạy. Worker xử lý lần lượt, một job đồng thời.

    ⚠️ Đổi mô hình nhúng: đổi ``EMBED_URL`` của WORKER trước, chạy lệnh này, đợi xong rồi mới đổi
    ``EMBED_URL`` của API — truy hồi lọc đoạn theo mô hình của chính vector câu hỏi (ADR-0031).
    """
    cac = await document_repository.tai_lieu_can_nap_lai(session)
    for t in cac:
        await document_repository.tao_ban_bong(session, t)
    logger.info("kiem_toan_kho thao_tac=NAP_LAI_TOAN_KHO so_tai_lieu=%d", len(cac))
    return ReindexTenantAccepted(tenant_id=UUID(tenant_id), total_documents=len(cac))


async def delete_document(session: AsyncSession, document_id: UUID) -> DocumentDeleted:
    """Gỡ khỏi chỉ mục: xoá đoạn TRƯỚC rồi ``ARCHIVED``, cùng transaction — hỏng giữa chừng thì
    rollback, trạng thái giữ nguyên (đặc tả UC020 luồng phụ 7.2). Gỡ lại tài liệu đã gỡ: luỹ
    đẳng."""
    t = await _lay_hoac_404(session, document_id, khoa=True)
    if t.status == "ARCHIVED":
        return DocumentDeleted(message="Tài liệu đã được gỡ trước đó", chunks_deleted=0)
    if t.status in _DANG_NAP or t.reindex_document_id is not None:
        raise DocumentBusyError(f"Tài liệu {document_id} đang được nạp — thử lại sau")
    so = await document_repository.xoa_khoi_chi_muc(session, document_id)
    _kiem_toan("GO", document_id, so_doan=so)
    return DocumentDeleted(message="Đã gỡ tài liệu khỏi kho tri thức", chunks_deleted=so)


# ── UC026 — tóm tắt hội thoại (ADR-0032) ─────────────────────────────────────

TriggerTomTat = Literal["HANDOFF", "CLOSING", "TURN_THRESHOLD", "MANUAL"]


@dataclass(frozen=True, slots=True)
class KetQuaTomTatHoiThoai:
    """Kết cục một lượt ``summarize``.

    ``DA_GHI``         đã PATCH sang java-core + ghi ``ai_interactions`` nhánh ``SUMMARY``.
    ``BO_QUA_NGAN``    dưới ngưỡng tin nhắn của khách — 0 lời gọi LLM (luồng phụ 1.1).
    ``TRUNG``          sự kiện đã xử lý từ trước (luồng phụ 1.2).
    ``SAI_DINH_DANG``  vẫn thiếu phần sau một vòng sửa — bản cũ giữ nguyên (luồng phụ 3.1).
    """

    trang_thai: Literal["DA_GHI", "BO_QUA_NGAN", "TRUNG", "SAI_DINH_DANG"]
    ban_ghi: BanGhiTomTat | None = None
    interaction_id: UUID | None = None
    so_lan_goi_llm: int = 0
    loi: str | None = None


def tao_bo_tom_tat(settings=None, *, transport=None) -> tom_tat.BoTomTat:
    """Bộ tóm tắt — client LLM RIÊNG với lượt chat, vì hai lẽ:

    - ``temperature`` GHIM ở ``tom_tat.NHIET_DO`` (= 0), không đọc ``LLM_TEMPERATURE`` (ADR-0032);
    - mạch riêng + hạn chót rộng (``tom_tat_han_chot_s``): chạy nền, không ai chờ, và một loạt hội
      thoại đóng cùng lúc làm mở mạch thì khách đang chat không phải nhận câu suy giảm vì nó.

    ``transport`` chỉ để test tiêm ``httpx.MockTransport`` và kiểm thân request thật.
    """
    s = settings or get_settings()
    if s.llm_mode == "mock":
        client = MockLLMClient(noi_dung=tom_tat.DAU_RA_GIA)
    else:
        if not s.llm_api_key:
            raise ValueError("LLM_MODE=remote nhưng LLM_API_KEY trống — điền khoá vào .env")
        client = OpenAICompatLLMClient(
            base_url=s.llm_base_url,
            api_key=s.llm_api_key,
            model=s.llm_model,
            temperature=tom_tat.NHIET_DO,
            max_tokens=s.tom_tat_max_tokens,
            reasoning_effort=s.llm_reasoning_effort,
            transport=transport,
        )
    return tom_tat.BoTomTat(
        LLMChiuLoi(
            client,
            CircuitBreaker(
                nguong_hong=s.llm_breaker_nguong_hong, thoi_gian_mo_s=s.llm_breaker_thoi_gian_mo_s
            ),
            han_chot_s=s.tom_tat_han_chot_s,
        ),
        ky_tu_moi_khoi=s.tom_tat_ky_tu_moi_khoi,
    )


# Một bộ tóm tắt mỗi event loop — cùng lý do với ``_TRA_LOI``: mạch phải nhớ lượt hỏng trước.
_TOM_TAT: dict[int, tom_tat.BoTomTat] = {}


def _bo_tom_tat() -> tom_tat.BoTomTat:
    loop = id(asyncio.get_running_loop())
    bo = _TOM_TAT.get(loop)
    if bo is None:
        bo = tao_bo_tom_tat()
        _TOM_TAT[loop] = bo
    return bo


async def _ghi_luot_tom_tat(
    tenant_id: str,
    conversation_id: UUID,
    trigger: str,
    kq: tom_tat.KetQuaTomTat | None,
    *,
    so_tin: int,
    loi: str | None,
    su_kien: SuKienNap | None,
    factory: SessionFactory,
) -> UUID:
    """Một dòng ``ai_interactions`` nhánh ``SUMMARY`` + (nếu có) dòng chống trùng, CÙNG transaction.

    ``response_text`` là JSON bốn phần — bản tóm tắt cũ truy lại được từ đây khi java-core đã ghi
    đè bản mới (đặc tả UC026 luồng phụ 4.1: "không có bảng tóm tắt riêng"). Nội dung đã che PII từ
    đầu vào. Lượt hỏng ghi ``FAILED`` + ``LOW_CONFIDENCE`` theo đúng quy ước lượt hỏng của
    ``orchestrator/turn.py`` — CHECK ``ck_interaction_refusal`` đòi một lý do khi không trả lời.
    """
    s = get_settings()
    vao = kq.prompt_tokens if kq else 0
    ra = kq.completion_tokens if kq else 0
    interaction_id = uuid4()
    async with get_tenant_session(tenant_id, factory) as phien:
        await interaction_repository.ghi_luot(
            phien,
            id=interaction_id,
            conversation_id=str(conversation_id),
            branch="SUMMARY",
            intent=f"summary:{trigger}"[:50],
            intent_confidence=None,
            user_query=f"[UC026 {trigger}] tóm tắt {so_tin} tin nhắn",
            response_text=kq.tom_tat.model_dump_json(by_alias=True) if kq else None,
            retrieved_chunk_ids=[],
            retrieval_top_score=None,
            is_answered=loi is None,
            refusal_reason=None if loi is None else "LOW_CONFIDENCE",
            model_name=kq.model_name if kq else s.llm_model,
            model_version=kq.model_version if kq else None,
            prompt_tokens=vao,
            completion_tokens=ra,
            cost_vnd=round(
                (vao * s.llm_gia_vao_vnd_trieu_token + ra * s.llm_gia_ra_vnd_trieu_token)
                / 1_000_000,
                4,
            ),
            latency_ms=kq.latency_ms if kq else 0,
            status="SUCCESS" if loi is None else "FAILED",
            error_message=loi,
            safety_flag=None,
            groundedness_score=None,
            llm_called=True,
            is_degraded=False,
            is_handoff=False,
        )
        if su_kien is not None:
            await processed_event_repository.ghi_nhan(
                phien, su_kien.consumer_group, su_kien.event_id, conversation_id
            )
    return interaction_id


async def _danh_dau_su_kien(
    tenant_id: str, conversation_id: UUID, su_kien: SuKienNap | None, factory: SessionFactory
) -> None:
    if su_kien is None:
        return
    async with get_tenant_session(tenant_id, factory) as phien:
        await processed_event_repository.ghi_nhan(
            phien, su_kien.consumer_group, su_kien.event_id, conversation_id
        )


async def summarize(
    tenant_id: str,
    conversation_id: UUID,
    *,
    trigger: TriggerTomTat = "CLOSING",
    su_kien: SuKienNap | None = None,
    java_core: JavaCoreClient | None = None,
    bo_tom_tat: tom_tat.BoTomTat | None = None,
    factory: SessionFactory = None,
) -> KetQuaTomTatHoiThoai:
    """UC026 bước 1–6, đường bất đồng bộ (worker, ``crm.conversation.closed``).

    THỨ TỰ — và vì sao không gom được vào một transaction như UC019:
    tác động chính là PATCH sang java-core (HTTP), không thể chung transaction với
    ``ai.processed_events``. Nên:

        1. kiểm sớm ``da_xu_ly`` — sự kiện trùng thì khỏi tốn LLM;
        2. đọc lịch sử qua java-core;
        3. luật: quá ít tin của khách ⇒ đánh dấu xong, 0 LLM;
        4. sinh bốn phần (LLM, ``temperature = 0``);
        5. PATCH sang java-core — LUỸ ĐẲNG (ghi đè bản mới nhất);
        6. CÙNG một transaction: dòng ``SUMMARY`` + dòng chống trùng.

    Chết giữa 5 và 6 ⇒ Kafka giao lại ⇒ tóm tắt + PATCH lần nữa: vô hại (cùng nội dung ở nhiệt độ
    0), chỉ tốn thêm một lượt LLM. Đảo thứ tự (đánh dấu trước, PATCH sau) thì chết giữa chừng là
    sự kiện "xong" mà hội thoại không có tóm tắt — mất việc, tệ hơn hẳn làm thừa.

    Lỗi TẠM THỜI (``SummaryLlmError``, ``JavaCoreUnavailableError``, CSDL) thoát ra ngoài — worker
    thử lại rồi DLQ, không xác nhận offset ngay (đặc tả UC026 ``LLM_ERROR``).
    """
    s = get_settings()
    java_core = java_core or tao_java_core_client(s)
    bo = bo_tom_tat or _bo_tom_tat()

    if su_kien is not None:
        async with get_tenant_session(tenant_id, factory) as phien:
            if await processed_event_repository.da_xu_ly(
                phien, su_kien.consumer_group, su_kien.event_id
            ):
                summaries.labels(trigger=trigger, outcome="TRUNG").inc()
                return KetQuaTomTatHoiThoai("TRUNG")

    cac_tin = await java_core.lay_tin_nhan(tenant_id, conversation_id)
    if tom_tat.dem_tin_khach(cac_tin) < s.tom_tat_so_tin_khach_toi_thieu:
        await _danh_dau_su_kien(tenant_id, conversation_id, su_kien, factory)
        summaries.labels(trigger=trigger, outcome="BO_QUA_NGAN").inc()
        logger.info("Tóm tắt %s: bỏ qua — %d tin, quá ngắn", conversation_id, len(cac_tin))
        return KetQuaTomTatHoiThoai("BO_QUA_NGAN")

    try:
        kq = await bo.tom_tat(cac_tin)
    except SummarySchemaInvalidError as loi:
        # Vĩnh viễn với lịch sử này (nhiệt độ 0) — ghi nhận lỗi, giữ bản cũ, KHÔNG thử lại.
        await _ghi_luot_tom_tat(
            tenant_id, conversation_id, trigger, None,
            so_tin=len(cac_tin), loi=loi.code, su_kien=su_kien, factory=factory,
        )
        summaries.labels(trigger=trigger, outcome="SAI_DINH_DANG").inc()
        logger.warning("Tóm tắt %s: %s — giữ bản cũ", conversation_id, loi)
        return KetQuaTomTatHoiThoai("SAI_DINH_DANG", loi=loi.code)

    ban_ghi = BanGhiTomTat(
        trigger=trigger,
        main_need=kq.tom_tat.main_need,
        provided_info=kq.tom_tat.provided_info,
        unresolved_issues=kq.tom_tat.unresolved_issues,
        next_steps=kq.tom_tat.next_steps,
        model_version=kq.model_version,
        summary_text=kq.tom_tat.ban_phang(),
        generated_at=bay_gio(),
    )
    await java_core.ghi_tom_tat(tenant_id, conversation_id, ban_ghi)
    interaction_id = await _ghi_luot_tom_tat(
        tenant_id, conversation_id, trigger, kq,
        so_tin=len(cac_tin), loi=None, su_kien=su_kien, factory=factory,
    )
    summaries.labels(trigger=trigger, outcome="DA_GHI").inc()
    logger.info(
        "Tóm tắt %s: %s, %d lượt LLM, %d khối, sửa=%s",
        conversation_id, kq.model_version, kq.so_lan_goi, kq.so_khoi, kq.da_sua,
    )
    return KetQuaTomTatHoiThoai("DA_GHI", ban_ghi, interaction_id, kq.so_lan_goi)


async def summarize_messages(
    tenant_id: str,
    yeu_cau: SummarizeRequest,
    *,
    bo_tom_tat: tom_tat.BoTomTat | None = None,
    factory: SessionFactory = None,
) -> SummarizeResponse:
    """UC026, đường ĐỒNG BỘ ``POST /v1/ai/summarize``: java-core gửi kèm lịch sử, nhận bốn phần về
    và tự ghi (nút "tóm tắt lại" — trigger ``MANUAL``). Không PATCH ngược sang java-core.

    Cùng bộ tóm tắt, cùng luật bỏ qua — chỉ khác: quá ngắn thì báo lỗi rõ (người bấm đang chờ), sai
    định dạng thì ném ``SummarySchemaInvalidError`` (đã ghi ``FAILED`` trước khi ném).
    """
    s = get_settings()
    bo = bo_tom_tat or _bo_tom_tat()
    cac_tin = [
        TinNhanHoiThoai(nguoi_gui=m.sender, noi_dung=m.text, gui_luc=m.created_at)
        for m in yeu_cau.messages
    ]
    if tom_tat.dem_tin_khach(cac_tin) < s.tom_tat_so_tin_khach_toi_thieu:
        raise ConversationTooShortError(
            f"Cần ít nhất {s.tom_tat_so_tin_khach_toi_thieu} tin nhắn của khách để tóm tắt"
        )
    try:
        kq = await bo.tom_tat(cac_tin)
    except SummarySchemaInvalidError as loi:
        await _ghi_luot_tom_tat(
            tenant_id, yeu_cau.conversation_id, yeu_cau.trigger, None,
            so_tin=len(cac_tin), loi=loi.code, su_kien=None, factory=factory,
        )
        summaries.labels(trigger=yeu_cau.trigger, outcome="SAI_DINH_DANG").inc()
        raise
    interaction_id = await _ghi_luot_tom_tat(
        tenant_id, yeu_cau.conversation_id, yeu_cau.trigger, kq,
        so_tin=len(cac_tin), loi=None, su_kien=None, factory=factory,
    )
    summaries.labels(trigger=yeu_cau.trigger, outcome="DA_GHI").inc()
    return SummarizeResponse(
        trigger=yeu_cau.trigger,
        main_need=kq.tom_tat.main_need,
        provided_info=kq.tom_tat.provided_info,
        unresolved_issues=kq.tom_tat.unresolved_issues,
        next_steps=kq.tom_tat.next_steps,
        model_version=kq.model_version,
        summary_text=kq.tom_tat.ban_phang(),
        generated_at=bay_gio(),
        interaction_id=interaction_id,
    )


# ── UC041 — xoá dữ liệu cá nhân (ADR-0033) ───────────────────────────────────

GHI_CHU_GIOI_HAN_XOA = (
    "Phạm vi xoá phía AI: tài liệu tri thức gắn với khách (kể cả tệp gốc), mọi lượt xử lý AI và "
    "đánh giá của các hội thoại được gửi kèm, đặc trưng lead. KHÔNG vươn tới hệ thống bên ngoài đã "
    "nhận dữ liệu qua MCP, và không tới nhà cung cấp LLM — nội dung gửi đi đã che số điện thoại, "
    "email, CCCD nhưng không xoá được ở phía họ."
)


async def forget_contact(
    tenant_id: str,
    contact_id: UUID,
    conversation_ids: Sequence[UUID],
    *,
    java_core: JavaCoreClient | None = None,
    factory: SessionFactory = None,
) -> ErasureResult:
    """UC041 — xoá dữ liệu cá nhân của MỘT khách ở phía Track B. LUỸ ĐẲNG: gọi lại sau khi đã xoá
    thì mọi mục ra 0 dòng ``DONE``; gọi lại sau ``PARTIALLY_FAILED`` thì làm nốt phần hỏng.

    Ba chặng, mỗi chặng một mục trong kết quả — đặc tả: "tiến độ theo từng bảng":

    1. MỘT transaction CSDL: tài liệu + đoạn của khách, lượt + đánh giá của các hội thoại. Commit
       TRƯỚC khi chạm hệ thống ngoài — truy hồi ngừng thấy dữ liệu đó ngay tại commit, nên câu trả
       lời sinh sau đó không thể trích nó. Hỏng ở đây thì ném (500) — chưa xoá gì, java-core gọi
       lại.
    2. Tệp gốc trên S3 — sau commit: S3 hỏng thì tệp còn nhưng không dòng nào trỏ tới, không truy
       hồi được; mục ghi ``FAILED`` để lần gọi lại xoá tiếp.
    3. Đặc trưng lead QUA API java-core (``sales.lead_scores``, ADR-0016 — không có
       ``ai.lead_features``). java-core sập ⇒ mục ``FAILED``, không kết luận cả yêu cầu (luồng phụ
       9.1 nhìn từ phía ai-service).

    Bên AI KHÔNG tự khởi động việc xoá — chỉ chạy khi java-core gọi, sau bước xác minh danh tính
    (chốt ``X-Internal-Token`` ở tầng API). Số tổng hợp (``GET /v1/ai/quality``) tính trực tiếp từ
    bảng nên giảm theo — không có bảng tổng hợp nào của Track B để "giữ ở dạng tổng hợp".
    """
    s = get_settings()
    java_core = java_core or tao_java_core_client(s)

    async with get_tenant_session(tenant_id, factory) as phien:
        tai_lieu = await document_repository.xoa_tai_lieu_theo_khach(phien, contact_id)
        luot = await interaction_repository.xoa_theo_hoi_thoai(phien, conversation_ids)

    cac_muc = [
        ErasureItem(target_schema="knowledge", target_table="knowledge_documents", action="DELETE",
                    status="DONE", affected_rows=tai_lieu.so_tai_lieu),
        ErasureItem(target_schema="knowledge", target_table="knowledge_chunks", action="DELETE",
                    status="DONE", affected_rows=tai_lieu.so_doan),
        ErasureItem(target_schema="ai", target_table="ai_interactions", action="DELETE",
                    status="DONE", affected_rows=luot.so_luot),
        ErasureItem(target_schema="ai", target_table="ai_feedback", action="DELETE",
                    status="DONE", affected_rows=luot.so_danh_gia),
        ErasureItem(target_schema="ai", target_table="ai_tool_calls", action="DELETE",
                    status="DONE", affected_rows=luot.so_goi_cong_cu),
    ]

    # ── 2. Tệp gốc ───────────────────────────────────────────────────────────
    so_tep = 0
    loi_tep: str | None = None
    for uri in tai_lieu.cac_tep:
        try:
            key = kiem_uri_thuoc_tenant(uri, tenant_id, s.s3_bucket)
            await asyncio.to_thread(object_storage.xoa, s.s3_bucket, key)
            so_tep += 1
        except (ForbiddenFileUriError, StorageUnavailableError) as loi:
            # ForbiddenFileUri: đường dẫn ngoài vùng tenant — KHÔNG BAO GIỜ xoá thứ đó.
            loi_tep = loi.code
            logger.warning("UC041: không xoá được một tệp gốc (%s)", loi.code)
    cac_muc.append(
        ErasureItem(target_schema="s3", target_table=s.s3_bucket, action="DELETE",
                    status="FAILED" if loi_tep else "DONE", affected_rows=so_tep,
                    error_code=loi_tep)
    )

    # ── 3. Đặc trưng lead qua java-core ──────────────────────────────────────
    try:
        so_lead = await java_core.xoa_dac_trung_lead(tenant_id, contact_id)
        cac_muc.append(
            ErasureItem(target_schema="sales", target_table="lead_scores", action="DELETE",
                        status="DONE", affected_rows=so_lead)
        )
    except AiServiceError as loi:
        logger.warning("UC041: java-core không xoá được đặc trưng lead (%s)", loi.code)
        cac_muc.append(
            ErasureItem(target_schema="sales", target_table="lead_scores", action="DELETE",
                        status="FAILED", affected_rows=0, error_code=loi.code)
        )

    for m in cac_muc:
        if m.affected_rows:
            privacy_erasures.labels(table=f"{m.target_schema}.{m.target_table}").inc(
                m.affected_rows
            )
    trang_thai = "COMPLETED" if all(m.status == "DONE" for m in cac_muc) else "PARTIALLY_FAILED"
    # Nhật ký kiểm toán: định danh + số đếm, KHÔNG nội dung. Biên bản chính thức là của java-core
    # (platform.audit_logs) — ai-service không ghi schema của Track A.
    logger.info(
        "kiem_toan_rieng_tu thao_tac=XOA_DU_LIEU_CA_NHAN khach=%s so_hoi_thoai=%d trang_thai=%s %s",
        contact_id, len(conversation_ids), trang_thai,
        " ".join(f"{m.target_schema}.{m.target_table}={m.affected_rows}" for m in cac_muc),
    )
    return ErasureResult(
        contact_id=contact_id, status=trang_thai, items=cac_muc, note=GHI_CHU_GIOI_HAN_XOA
    )
