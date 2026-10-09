"""HTTP client gọi java-core — bề mặt DUY NHẤT chạm dữ liệu nghiệp vụ (ADR-0002).

Đặc tả: docs/openapi/java-core-to-ai-service.yaml. Mọi request mang X-Tenant-Id và X-Trace-Id.

    client.py   giao thức JavaCoreClient + HttpJavaCoreClient + MockJavaCoreClient
"""

from src.ai.config import Settings, get_settings
from src.ai.integrations.java_core.client import (
    BanGhiTomTat,
    HttpJavaCoreClient,
    JavaCoreClient,
    MockJavaCoreClient,
    TinNhanHoiThoai,
)

# Bản giả DÙNG CHUNG trong một tiến trình ở chế độ mock: API và worker là hai tiến trình nên không
# chia sẻ được, nhưng trong một tiến trình thì lịch sử nạp ở test/minh chứng phải nhìn thấy được từ
# mọi nơi gọi facade.
_GIA: MockJavaCoreClient | None = None


def tao_java_core_client(settings: Settings | None = None) -> JavaCoreClient:
    """Chọn hiện thực theo ``JAVA_CORE_MODE``."""
    global _GIA
    settings = settings or get_settings()
    if settings.java_core_mode == "mock":
        if _GIA is None:
            _GIA = MockJavaCoreClient()
        return _GIA
    return HttpJavaCoreClient(
        base_url=settings.java_core_url, timeout_s=settings.java_core_timeout_s
    )


__all__ = [
    "BanGhiTomTat",
    "HttpJavaCoreClient",
    "JavaCoreClient",
    "MockJavaCoreClient",
    "TinNhanHoiThoai",
    "tao_java_core_client",
]
