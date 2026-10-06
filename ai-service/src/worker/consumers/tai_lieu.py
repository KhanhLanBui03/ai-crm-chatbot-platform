"""Consumer ``ingestion-cg`` của ``crm.kb.document.uploaded`` — UC019. [PRODUCTION]

Tách khỏi ``src/worker/main.py`` để kiểm được TOÀN BỘ quyết định "commit hay DLQ" mà không cần
Kafka: lớp này nhận bytes + header của một bản tin, trả về việc worker phải làm với offset.

Ba tầng thử lại, mỗi tầng một lý do — đừng gộp:

    tầng        ai đếm                 thử lại khi                   hết lượt thì
    ─────────   ────────────────────   ───────────────────────────   ─────────────────────────────
    lượt nạp    attempt_count (CSDL)   ``THU_LAI``: S3/ai-embed chết  FAILED INGEST_RETRY_EXHAUSTED
    bản tin     vòng lặp ở đây          ngoại lệ thoát khỏi service   DLQ (sự kiện chưa thành
                                       (thường là CSDL chết)         trạng thái tài liệu nào)
    tiến trình  bộ quét (updated_at)   worker chết giữa chừng        FAILED INGEST_STALLED

Lượt nạp đếm trong CSDL vì nó phải sống qua lần khởi động lại; bản tin đếm trong bộ nhớ vì khởi
động lại thì Kafka giao lại bản tin chưa xác nhận — đếm lại từ đầu là đúng.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai import service
from src.ai.events.dlq import doc_header
from src.ai.events.su_kien_tai_lieu import giai_ma
from src.ai.exceptions import AiServiceError, EventSchemaInvalidError, EventUnsupportedError
from src.ai.inference.clients import EmbedClient
from src.ai.telemetry.logging import tenant_id_var, trace_id_var

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KetQuaBanTin:
    """Việc worker phải làm với offset của bản tin vừa xử lý.

    ``COMMIT``: xác nhận offset — việc của sự kiện đã xong (kể cả khi tài liệu ``FAILED``: đó là
    kết cục hợp lệ, đã ghi lên tài liệu).
    ``DLQ``: phát bản tin gốc sang ``ai.dlq`` kèm ``ma_loi``, RỒI MỚI xác nhận offset.
    """

    hanh_dong: Literal["COMMIT", "DLQ"]
    ma_loi: str | None = None
    thong_diep: str | None = None
    ket_qua_nap: service.KetQuaNap | None = None


def _cho_lan(cho_s: Sequence[float], lan_thu: int) -> float:
    """Chờ trước lần thử thứ ``lan_thu + 1`` (đếm từ 0); hết danh sách thì dùng số cuối."""
    if not cho_s:
        return 0.0
    return cho_s[min(lan_thu, len(cho_s) - 1)]


class XuLyTaiLieu:
    """Chạy job nạp dưới semaphore MỘT job, và quyết định số phận từng bản tin."""

    def __init__(
        self,
        *,
        embed: EmbedClient,
        consumer_group: str,
        so_luot_toi_da: int,
        cho_thu_lai_s: Sequence[float],
        so_lan_thu_ban_tin: int = 3,
        factory: async_sessionmaker[AsyncSession] | None = None,
        ngu: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.embed = embed
        self.consumer_group = consumer_group
        self.so_luot_toi_da = so_luot_toi_da
        self.cho_thu_lai_s = tuple(cho_thu_lai_s)
        self.so_lan_thu_ban_tin = so_lan_thu_ban_tin
        self.factory = factory
        self._ngu = ngu
        # ĐÚNG MỘT job nạp tại một thời điểm trong tiến trình này — dùng chung giữa luồng Kafka và
        # bộ quét (và UC020 ở Ngày 11). Một job giữ: một tiến trình con phân tích (bo_phan_tich chỉ
        # có 1 worker), một lô vector trong RAM, một kết nối CSDL. Hai job song song là gấp đôi cả
        # ba trên pod có giới hạn bộ nhớ, trong khi ai-embed trên CPU không nhanh hơn chút nào.
        # Muốn nạp nhanh hơn thì tăng replica worker (cùng group, Kafka chia partition), không
        # tăng số này.
        self._mot_job = asyncio.Semaphore(1)

    async def chay_job(
        self,
        tenant_id: str,
        document_id: UUID,
        su_kien: service.SuKienNap | None = None,
    ) -> service.KetQuaNap:
        """Nạp một tài liệu tới kết cục, tự thử lại khi ``THU_LAI``.

        Semaphore giữ trong TỪNG lượt, nhả trong lúc chờ thử lại — bộ quét và bản tin khác không
        phải xếp hàng sau 30 giây ngủ của một tài liệu đang chờ S3 sống lại.

        Sự kiện chỉ đi kèm lượt ĐẦU: ``THU_LAI`` nghĩa là bước nhận việc đã commit cùng dòng
        ``ai.processed_events`` — gửi lại sự kiện ở lượt sau sẽ bị coi là trùng.
        """
        for lan_thu in range(self.so_luot_toi_da):
            async with self._mot_job:
                ket_qua = await service.nap_tai_lieu(
                    tenant_id,
                    document_id,
                    embed=self.embed,
                    su_kien=su_kien if lan_thu == 0 else None,
                    factory=self.factory,
                )
            logger.info(
                "Nạp tài liệu %s: %s (lượt %s, %s đoạn, lỗi %s)",
                document_id, ket_qua.trang_thai, ket_qua.lan, ket_qua.so_doan, ket_qua.loi,
            )
            if ket_qua.trang_thai != "THU_LAI":
                return ket_qua
            await self._ngu(_cho_lan(self.cho_thu_lai_s, lan_thu))
        # attempt_count trong CSDL chặn trước khi tới đây (lượt cuối ra FAILED, không THU_LAI);
        # vòng for chỉ là trần phòng thủ nếu cấu hình hai bên lệch nhau.
        return ket_qua

    async def xu_ly_ban_tin(
        self, gia_tri: bytes | None, headers: Sequence[tuple[str, bytes]] | None
    ) -> KetQuaBanTin:
        """Một bản tin → ``COMMIT`` hoặc ``DLQ``. KHÔNG ném ra, trừ khi bị huỷ (tắt worker)."""
        trace_id_var.set(doc_header(headers, "X-Trace-Id") or "-")
        tenant_id_var.set("-")

        try:
            su_kien = giai_ma(gia_tri)
        except (EventSchemaInvalidError, EventUnsupportedError) as loi:
            logger.error("Bản tin hỏng lược đồ → DLQ: %s: %s", loi.code, loi)
            return KetQuaBanTin("DLQ", loi.code, str(loi))

        tenant_id_var.set(su_kien.tenant_id)
        dinh_danh = service.SuKienNap(self.consumer_group, su_kien.event_id)

        loi_cuoi: Exception | None = None
        for lan_thu in range(self.so_lan_thu_ban_tin):
            try:
                ket_qua = await self.chay_job(su_kien.tenant_id, su_kien.document_id, dinh_danh)
                return KetQuaBanTin("COMMIT", ket_qua_nap=ket_qua)
            except Exception as loi:  # noqa: BLE001 — mọi lỗi thoát khỏi service đều thử lại
                loi_cuoi = loi
                logger.warning(
                    "Sự kiện %s lần %s/%s hỏng: %s",
                    su_kien.event_id, lan_thu + 1, self.so_lan_thu_ban_tin, loi, exc_info=loi,
                )
                if lan_thu + 1 < self.so_lan_thu_ban_tin:
                    await self._ngu(_cho_lan(self.cho_thu_lai_s, lan_thu))

        ma = loi_cuoi.code if isinstance(loi_cuoi, AiServiceError) else type(loi_cuoi).__name__
        return KetQuaBanTin(
            "DLQ",
            "RETRY_EXHAUSTED",
            f"{ma} sau {self.so_lan_thu_ban_tin} lần thử — xem log theo X-Trace-Id",
        )
