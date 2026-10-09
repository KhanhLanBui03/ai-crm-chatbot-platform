"""Consumer ``summarizer-cg`` của ``crm.conversation.closed`` — UC026. [PRODUCTION]

Cùng khuôn với ``tai_lieu.py``: lớp này nhận bytes + header của một bản tin và trả về việc worker
phải làm với offset — kiểm được trọn quyết định "commit hay DLQ" mà không cần Kafka.

    kết cục của service.summarize          bản tin
    ─────────────────────────────────────  ──────────────────────────────────────────────
    DA_GHI · BO_QUA_NGAN · TRUNG           COMMIT
    SAI_DINH_DANG (vẫn thiếu phần sau sửa) COMMIT — đã ghi FAILED, bản cũ giữ nguyên; ở nhiệt
                                           độ 0 thử lại chỉ ra lại đúng đầu ra hỏng đó
    ngoại lệ (LLM_ERROR, java-core, CSDL)  thử lại tại chỗ ``so_lan_thu_ban_tin`` lần, rồi DLQ

LỆCH CÓ CHỦ ĐÍCH so với chữ của đặc tả (``LLM_ERROR`` — "không xác nhận offset để sự kiện được
nhận lại"): không xác nhận MÃI thì một hội thoại có LLM sập chặn cả partition phía sau nó (Kafka
giao theo thứ tự). Thử lại tại chỗ với khoảng chờ dài hơn UC019 rồi đẩy DLQ giữ NGUYÊN BYTE bản tin
— phát lại được bằng tay khi nhà cung cấp sống lại (ADR-0024, ADR-0032).

Bản tin mang ``conversation_id``, không mang lịch sử; tenant của vỏ đặt ngữ cảnh log và đi theo mọi
lời gọi java-core làm ``X-Tenant-Id``.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai import service
from src.ai.events.dlq import doc_header
from src.ai.events.su_kien_hoi_thoai_dong import giai_ma
from src.ai.exceptions import AiServiceError, EventSchemaInvalidError, EventUnsupportedError
from src.ai.integrations.java_core import JavaCoreClient
from src.ai.rag.generate.tom_tat import BoTomTat
from src.ai.telemetry.logging import tenant_id_var, trace_id_var
from src.worker.consumers.tai_lieu import KetQuaBanTin, _cho_lan

logger = logging.getLogger(__name__)


class XuLyTomTat:
    """Một hội thoại đóng → một lượt ``service.summarize`` với trigger ``CLOSING``."""

    def __init__(
        self,
        *,
        consumer_group: str,
        java_core: JavaCoreClient | None = None,
        bo_tom_tat: BoTomTat | None = None,
        so_lan_thu_ban_tin: int = 3,
        cho_thu_lai_s: Sequence[float] = (10.0, 60.0),
        factory: async_sessionmaker[AsyncSession] | None = None,
        ngu: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.consumer_group = consumer_group
        self.java_core = java_core
        self.bo_tom_tat = bo_tom_tat
        self.so_lan_thu_ban_tin = so_lan_thu_ban_tin
        self.cho_thu_lai_s = tuple(cho_thu_lai_s)
        self.factory = factory
        self._ngu = ngu

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
                ket_qua = await service.summarize(
                    su_kien.tenant_id,
                    su_kien.conversation_id,
                    trigger="CLOSING",
                    su_kien=dinh_danh,
                    java_core=self.java_core,
                    bo_tom_tat=self.bo_tom_tat,
                    factory=self.factory,
                )
                return KetQuaBanTin("COMMIT", ket_qua_tom_tat=ket_qua)
            except Exception as loi:  # noqa: BLE001 — mọi lỗi thoát khỏi service đều thử lại
                loi_cuoi = loi
                logger.warning(
                    "Sự kiện %s (tóm tắt) lần %s/%s hỏng: %s",
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
