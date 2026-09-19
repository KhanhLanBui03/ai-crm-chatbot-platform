"""Log JSON có Trace ID — kế hoạch mục 4.5, làm từ Sprint 0.

MẪU. Trace ID sinh ở gateway, đi xuyên suốt mọi chặng, và phải xuất hiện trên MỌI dòng log.
Không có nó thì việc truy vết một luồng đi qua gateway -> java-core -> ai-service là bất khả thi
khi hai người cùng gỡ lỗi.

Trace ID được giữ trong ``ContextVar`` chứ không truyền qua tham số hàm: một request FastAPI
chạy trên một task asyncio, và ContextVar bám theo task đó qua mọi lần ``await``.
"""

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

# Đặt bởi middleware ở đầu mỗi request, đọc bởi mọi dòng log phía dưới.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="-")


class ContextFilter(logging.Filter):
    """Chèn trace_id và tenant_id vào mọi bản ghi log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        record.tenant_id = tenant_id_var.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Cấu hình log JSON cho toàn ứng dụng. Gọi một lần lúc khởi động."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(trace_id)s %(tenant_id)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    )
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
