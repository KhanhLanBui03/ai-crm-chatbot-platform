"""Chạy bộ phân tích tệp ở TIẾN TRÌNH CON, đúng 1 worker, có trần thời gian — UC019. [PRODUCTION]

VÌ SAO TÁCH TIẾN TRÌNH
----------------------
pymupdf là thư viện C. Một PDF hỏng có thể làm nó treo vô hạn hoặc chết hẳn (segfault).
- Chạy trong luồng (``asyncio.to_thread``): treo thì không có cách nào dừng một luồng Python từ
  bên ngoài; chết thì chết CẢ service, kéo theo mọi request đang phục vụ.
- Chạy ở tiến trình con: treo thì ``terminate()`` được; chết thì chỉ tiến trình con chết,
  ``BrokenProcessPool`` báo về, service vẫn sống. Tài liệu đó chuyển ``FAILED``, tài liệu sau
  chạy tiếp trên một pool mới.

VÌ SAO ĐÚNG 1 WORKER
--------------------
``ProcessPoolExecutor()`` không tham số tạo ``os.cpu_count()`` tiến trình. Pod ai-service được
cấp ít vCPU và cùng lúc còn phục vụ chat: bốn PDF phân tích song song sẽ ăn hết CPU của lượt
chat — p95 ``/v1/ai/chat`` (< 4 s, §1.6) trả giá cho việc nạp tài liệu. Nạp tài liệu là việc
nền, chậm vài giây không ai thấy; chat chậm thì khách thấy ngay. Ngày 5 thêm semaphore giới
hạn đúng 1 job nạp đồng thời — hai lớp khớp nhau.

VÌ SAO ``spawn``
----------------
``fork`` (mặc định trên Linux) sao chép một tiến trình đang chạy vòng lặp asyncio, pool kết nối
CSDL và luồng của client S3 — tiến trình con thừa hưởng khoá đang bị giữ và có thể treo ngay
khi khởi động. ``spawn`` dựng một trình thông dịch sạch và chỉ import ``phan_tich.py`` (nhẹ,
không pyvi, không CSDL). Đánh đổi: khởi động tiến trình con chậm hơn ~0,5 s, trả một lần.
"""

import asyncio
import concurrent.futures
import multiprocessing
import threading
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from src.ai.exceptions import ParseFailedError, ParseTimeoutError
from src.ai.rag.ingest.phan_tich import Khoi, phan_tich_tep

# Tiến trình con được thay mới sau chừng này tệp: thư viện C (pymupdf) có thể rò bộ nhớ qua
# từng tệp — thay định kỳ thì RSS không phình mãi mà không cần biết rò ở đâu.
_SO_TEP_MOI_TIEN_TRINH = 50


class BoPhanTich:
    """Pool 1 tiến trình con, tự dựng lại sau khi phải giết hoặc sau khi tiến trình con chết."""

    def __init__(self) -> None:
        self._khoa = threading.Lock()
        self._pool: concurrent.futures.ProcessPoolExecutor | None = None

    def _lay_pool(self) -> concurrent.futures.ProcessPoolExecutor:
        with self._khoa:
            if self._pool is None:
                self._pool = concurrent.futures.ProcessPoolExecutor(
                    max_workers=1,
                    mp_context=multiprocessing.get_context("spawn"),
                    max_tasks_per_child=_SO_TEP_MOI_TIEN_TRINH,
                )
            return self._pool

    def _giet_pool(self) -> None:
        """Giết tiến trình con NGAY rồi bỏ pool — lần gọi sau dựng pool mới.

        ``shutdown(cancel_futures=True)`` KHÔNG dừng được tác vụ ĐANG chạy, chỉ huỷ tác vụ
        chưa chạy — tiến trình đang treo sẽ treo mãi. Không có API công khai nào để giết nó,
        nên phải chạm ``_processes`` (thuộc tính riêng, ổn định từ Python 3.2 tới 3.13). Đây là
        chỗ DUY NHẤT trong dự án dựa vào thuộc tính riêng của thư viện chuẩn; test
        ``test_tien_trinh`` sẽ đỏ nếu một bản Python sau đổi tên nó.
        """
        with self._khoa:
            pool, self._pool = self._pool, None
        if pool is None:
            return
        for tien_trinh in list((getattr(pool, "_processes", None) or {}).values()):
            tien_trinh.terminate()
        pool.shutdown(wait=False, cancel_futures=True)

    async def phan_tich(self, duong_dan: Path, source_type: str, timeout_s: float) -> list[Khoi]:
        """Phân tích ``duong_dan`` ở tiến trình con, chờ tối đa ``timeout_s`` giây.

        Ném lại nguyên ``NoTextExtractedError``/``ParseFailedError`` từ tiến trình con; ném
        ``ParseTimeoutError`` khi quá giờ, ``ParseFailedError`` khi tiến trình con chết.
        """
        pool = self._lay_pool()
        tuong_lai = pool.submit(phan_tich_tep, str(duong_dan), source_type)
        try:
            return await asyncio.wait_for(asyncio.wrap_future(tuong_lai), timeout=timeout_s)
        except TimeoutError:
            self._giet_pool()
            raise ParseTimeoutError(
                f"Phân tích {source_type} vượt {timeout_s:g} s — tệp có thể bị hỏng"
            ) from None
        except BrokenProcessPool:
            self._giet_pool()
            raise ParseFailedError(
                f"Tiến trình phân tích {source_type} chết giữa chừng — tệp có thể bị hỏng"
            ) from None

    def dong(self) -> None:
        """Gọi lúc tắt service (``lifespan``) để không bỏ lại tiến trình con mồ côi."""
        self._giet_pool()


# Một bộ phân tích cho cả tiến trình — cùng lý do với ``workers=1`` (ai-service/CLAUDE.md):
# tài nguyên nền không nhân bản.
bo_phan_tich = BoPhanTich()
