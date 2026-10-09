"""[PRODUCTION] Gọi LLM có chịu lỗi: thử lại TRONG hạn chót + circuit breaker — kế hoạch Ngày 9.

Nơi gọi chỉ thấy hai kết cục: ``KetQuaLLM``, hoặc ``LLMKhongKhaDung`` để chuyển sang câu trả lời
suy giảm (``degraded=true``). Không có đường nào để lỗi của nhà cung cấp lọt thành 5xx.

HẠN CHÓT CHUNG, KHÔNG PHẢI HẠN TỪNG LẦN
---------------------------------------
``han_chot_s`` (2,5 s, §5.3) là ngân sách cho CẢ chặng sinh, kể cả lần thử lại. Mỗi lần gọi chỉ
được phần thời gian còn lại. Hệ quả có chủ đích: lần đầu quá hạn đã ăn hết ngân sách ⇒ không thử
lại; ``429``/``503`` trả về nhanh ⇒ còn thời gian ⇒ thử lại một lần. Hạn từng lần 2,5 s cộng thử
lại sẽ thành 5 s và phá p95 < 4 s của /v1/ai/chat.

MỘT REQUEST GHI MỘT KẾT QUẢ VÀO MẠCH
-----------------------------------
Ghi sau khi đã thử lại xong, không ghi từng lần thử: mạch đếm "request không được phục vụ", nên
một request hỏng 2 lần không được đẩy mạch tới ngưỡng nhanh gấp đôi.
"""

import asyncio
import logging
import time
from collections.abc import Callable, Sequence

from src.ai.integrations.llm.circuit_breaker import CircuitBreaker
from src.ai.integrations.llm.client import KetQuaLLM, LLMClient, LLMError, TinNhan

logger = logging.getLogger(__name__)

# Dưới mức này không đủ cho một lượt khứ hồi tới nhà cung cấp — thử lại chỉ chắc chắn quá hạn.
THOI_GIAN_TOI_THIEU_S = 0.3
CHO_TRUOC_KHI_THU_LAI_S = 0.2
SO_LAN_THU_LAI = 1


class LLMKhongKhaDung(Exception):
    """Không có câu trả lời từ LLM cho request này. ``ma`` là lý do cho telemetry."""

    def __init__(self, ma: str, *, da_goi: bool) -> None:
        super().__init__(ma)
        self.ma = ma
        # False khi mạch đang mở — request không chạm tới nhà cung cấp (KPI lượt gọi LLM).
        self.da_goi = da_goi


class LLMChiuLoi:
    def __init__(
        self,
        client: LLMClient,
        breaker: CircuitBreaker,
        *,
        han_chot_s: float,
        dong_ho: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.breaker = breaker
        self._han_chot_s = han_chot_s
        self._dong_ho = dong_ho

    @property
    def model(self) -> str:
        return self.client.model

    async def chat(self, messages: Sequence[TinNhan]) -> KetQuaLLM:
        if not self.breaker.cho_phep():
            raise LLMKhongKhaDung("CIRCUIT_OPEN", da_goi=False)

        bat_dau = self._dong_ho()
        lan_thu_lai = 0
        while True:
            con_lai = self._han_chot_s - (self._dong_ho() - bat_dau)
            try:
                ket_qua = await self.client.chat(messages, timeout_s=con_lai)
            except LLMError as loi:
                if not loi.co_the_thu_lai:
                    # Nhà cung cấp đã trả lời — nó còn sống; lỗi ở phía mình (lời nhắc, khoá).
                    self.breaker.ghi_thanh_cong()
                    logger.error("LLM từ chối request, không thử lại: %s", loi)
                    raise LLMKhongKhaDung(loi.ma, da_goi=True) from loi

                con_lai = self._han_chot_s - (self._dong_ho() - bat_dau)
                het_luot = lan_thu_lai >= SO_LAN_THU_LAI
                if het_luot or con_lai < CHO_TRUOC_KHI_THU_LAI_S + THOI_GIAN_TOI_THIEU_S:
                    self.breaker.ghi_that_bai()
                    logger.warning(
                        "LLM không phục vụ được (%s), mạch %s", loi, self.breaker.trang_thai
                    )
                    raise LLMKhongKhaDung(loi.ma, da_goi=True) from loi

                lan_thu_lai += 1
                logger.info("LLM lỗi tạm thời (%s), thử lại, còn %.2f s", loi.ma, con_lai)
                await asyncio.sleep(CHO_TRUOC_KHI_THU_LAI_S)
                continue

            self.breaker.ghi_thanh_cong()
            return ket_qua

    async def aclose(self) -> None:
        await self.client.aclose()
