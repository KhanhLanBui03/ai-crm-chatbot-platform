"""Đăng ký ai-service với Eureka — kế hoạch mục 4.4.

MẪU, và là chỗ dễ mất nửa ngày nếu không biết trước, vì gần như mọi hướng dẫn về Eureka đều
giả định toàn bộ hệ thống viết bằng Java.

Ba điều bắt buộc:

1. FastAPI KHÔNG tự đăng ký. Phải gọi ``py-eureka-client`` lúc khởi động.
2. Phải HỦY ĐĂNG KÝ lúc tắt. Quên thì Eureka vẫn định tuyến tới một tiến trình đã chết
   trong khoảng 90 giây.
3. Bật ``prefer-ip-address``. Mặc định Eureka đăng ký bằng hostname container, và gateway
   thường không phân giải được hostname đó.
"""

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


async def register(settings: Settings) -> None:
    """Đăng ký với Eureka và bắt đầu gửi nhịp tim. Gọi trong lifespan lúc khởi động."""
    # TODO: eureka_client.init(eureka_server=settings.eureka_url,
    #                          app_name=settings.eureka_app_name,
    #                          instance_port=settings.ai_service_port,
    #                          prefer_ip_address=True,
    #                          renewal_interval_in_secs=10,
    #                          duration_in_secs=30)
    logger.info("Chưa cài đặt đăng ký Eureka — file mẫu")


async def deregister() -> None:
    """Hủy đăng ký. Gọi trong lifespan lúc tắt — KHÔNG được bỏ qua."""
    # TODO: eureka_client.stop()
    logger.info("Chưa cài đặt hủy đăng ký Eureka — file mẫu")
