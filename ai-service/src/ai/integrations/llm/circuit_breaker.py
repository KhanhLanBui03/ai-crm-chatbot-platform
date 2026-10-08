"""[PRODUCTION] Circuit breaker 3 trạng thái cho lời gọi LLM — kế hoạch Ngày 9, UC023.

::

    CLOSED ──(hỏng liên tiếp ≥ nguong_hong)──► OPEN ──(mở đủ thoi_gian_mo_s)──► HALF_OPEN
      ▲                                          ▲                                 │
      │                                          └──────(lượt thăm dò hỏng)────────┤
      └──────────────────────(lượt thăm dò thành công)─────────────────────────────┘

VÌ SAO KHÔNG CHỈ THỬ LẠI
------------------------
Thử lại chữa được lỗi chớp tắt của MỘT request. Khi nhà cung cấp sập hẳn, thử lại làm mọi
request chịu trọn hạn chót 2,5 s rồi mới hỏng — p95 /v1/ai/chat vọt lên trong khi không ai nhận
được câu trả lời nào. Mạch mở thì request hỏng NGAY (0 ms), lượt chat trả câu suy giảm
``degraded=true`` trong ngân sách độ trễ thay vì treo.

VÌ SAO CÓ HALF_OPEN
-------------------
Bỏ nó đi chỉ còn hai cách, cách nào cũng hỏng:

- hết thời gian mở là đóng hẳn — nhà cung cấp vẫn sập thì cả loạt request dồn tới cùng lúc, mỗi
  cái chịu trọn 2,5 s trước khi mạch mở lại (đúng cơn bão mà mạch sinh ra để chặn);
- không bao giờ tự đóng — nhà cung cấp sống lại rồi mà bot vẫn trả câu suy giảm tới khi khởi
  động lại pod.

HALF_OPEN cho đúng MỘT lượt thăm dò đi qua; các lượt khác vẫn bị chặn tới khi nó có kết quả.

ĐẾM GÌ LÀ HỎNG
--------------
Mạch đo SỨC SỐNG CỦA NHÀ CUNG CẤP, không đo đúng sai của từng request. Chỉ ``429``, ``5xx``,
quá hạn và lỗi mạng tính là hỏng. ``400``/``401``/``422`` nghĩa là nhà cung cấp đã trả lời —
lỗi nằm ở phía mình (lời nhắc, khoá), mở mạch vì chúng là phạt mọi người dùng vì một request.
Phân loại đó do ``chiu_loi.py`` làm; tệp này chỉ là máy trạng thái thuần, không I/O, để test
được cả ba trạng thái bằng một đồng hồ giả.

Chạy trong một event loop duy nhất (``workers=1``, §3.9.1) và không có ``await`` nào giữa đọc và
ghi trạng thái, nên không cần khoá.
"""

import time
from collections.abc import Callable
from enum import StrEnum


class TrangThai(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(
        self,
        *,
        nguong_hong: int = 3,
        thoi_gian_mo_s: float = 30.0,
        dong_ho: Callable[[], float] = time.monotonic,
    ) -> None:
        if nguong_hong < 1:
            raise ValueError("nguong_hong phải ≥ 1")
        self._nguong_hong = nguong_hong
        self._thoi_gian_mo_s = thoi_gian_mo_s
        self._dong_ho = dong_ho
        self._trang_thai = TrangThai.CLOSED
        self._hong_lien_tiep = 0
        self._mo_luc = 0.0
        # Lúc phát lượt thăm dò đang bay, None nếu không có. Lượt thăm dò bị huỷ giữa chừng
        # (client ngắt kết nối) thì không bao giờ báo kết quả — quá thoi_gian_mo_s thì cho lượt
        # khác thăm dò, nếu không mạch kẹt HALF_OPEN vĩnh viễn.
        self._tham_do_luc: float | None = None

    @property
    def trang_thai(self) -> TrangThai:
        return self._trang_thai

    def cho_phep(self) -> bool:
        """Request này có được gọi nhà cung cấp không.

        ``True`` ở HALF_OPEN nghĩa là request này LÀ lượt thăm dò.
        """
        bay_gio = self._dong_ho()
        if self._trang_thai is TrangThai.CLOSED:
            return True
        if self._trang_thai is TrangThai.OPEN:
            if bay_gio - self._mo_luc < self._thoi_gian_mo_s:
                return False
            self._trang_thai = TrangThai.HALF_OPEN
            self._tham_do_luc = bay_gio
            return True
        # HALF_OPEN
        if self._tham_do_luc is not None and bay_gio - self._tham_do_luc < self._thoi_gian_mo_s:
            return False
        self._tham_do_luc = bay_gio
        return True

    def ghi_thanh_cong(self) -> None:
        """Nhà cung cấp đã trả lời. Ở HALF_OPEN: lượt thăm dò qua ⇒ đóng mạch."""
        self._trang_thai = TrangThai.CLOSED
        self._hong_lien_tiep = 0
        self._tham_do_luc = None

    def ghi_that_bai(self) -> None:
        """Nhà cung cấp không trả lời được (429/5xx/quá hạn/lỗi mạng)."""
        if self._trang_thai is TrangThai.HALF_OPEN:
            # Thăm dò hỏng ⇒ mở lại ngay, đếm lại thời gian mở từ đầu.
            self._mo(self._dong_ho())
            return
        self._hong_lien_tiep += 1
        if self._hong_lien_tiep >= self._nguong_hong:
            self._mo(self._dong_ho())

    def _mo(self, luc: float) -> None:
        self._trang_thai = TrangThai.OPEN
        self._mo_luc = luc
        self._tham_do_luc = None
