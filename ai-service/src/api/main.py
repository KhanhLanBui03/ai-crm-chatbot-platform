"""Ứng dụng FastAPI — vai trò ``RUN_MODE=api``. Điểm vào của tiến trình là
``src/entrypoint.py``, không phải tệp này.

Dùng factory ``create_app()`` thay vì tạo ``app`` ở cấp module để kiểm thử dựng được
nhiều bản ứng dụng với cấu hình khác nhau mà không đụng biến toàn cục.

Vòng đời (``lifespan``) là chỗ duy nhất được phép khởi động và tắt tài nguyên nền:
đăng ký Eureka và huỷ đăng ký lúc tắt.

KHÔNG nạp model ở đây. Kiến trúc hai tầng v8.0 (§3.2) đưa toàn bộ model sang tầng
suy luận; đó là lý do pod sẵn sàng trong 2–5 giây thay vì 20–40 giây, và là điều kiện
để HPA phản ứng kịp khi tải tăng đột ngột (§3.2.3).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.ai import service
from src.ai.config import get_settings
from src.ai.inference.clients import aclose_http_clients
from src.ai.telemetry.logging import setup_logging
from src.api import eureka
from src.api.errors import dang_ky_xu_ly_loi
from src.api.v1.endpoints import health
from src.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Khởi động và tắt tài nguyên nền."""
    settings = get_settings()

    await eureka.register(settings)
    # UC023: dựng client nhúng + LLM ngay bây giờ — thiếu LLM_API_KEY ở LLM_MODE=remote thì pod
    # không lên, thay vì nổ ở lượt chat đầu tiên.
    await service.khoi_dong_tra_loi()
    # TODO: khởi động consumer Kafka (ingestion-cg) như một asyncio task nền.
    #       enable.auto.commit = False; xác nhận offset SAU KHI xử lý xong (mục 4.3).
    # TODO: nạp mô hình nhúng và mô hình xếp hạng lại — chậm, phải làm ở đây chứ không
    #       làm lúc phục vụ request đầu tiên.

    logger.info("ai-service đã khởi động")
    try:
        yield
    finally:
        # TODO: dừng consumer Kafka, chờ xử lý nốt bản tin đang dở
        await service.dong_tra_loi()
        await aclose_http_clients()
        await eureka.deregister()
        logger.info("ai-service đã tắt")


def create_app() -> FastAPI:
    """Dựng ứng dụng FastAPI."""
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="ai-service",
        description="Khối AI: RAG, LangGraph, MCP, chấm điểm Lead, phân nhóm chủ đề",
        version="0.1.0",
        lifespan=lifespan,
    )

    # TODO: middleware gắn X-Trace-Id vào ContextVar cho mọi request
    # TODO: /metrics cho Prometheus (prometheus-client)

    # AiServiceError → mã HTTP, lỗi validate → 422 kèm mã nghiệp vụ (src/api/errors.py).
    dang_ky_xu_ly_loi(app)

    # Bề mặt vận hành — KHÔNG đánh phiên bản. Docker Compose gọi /health, Prometheus gọi
    # /metrics; hai đường dẫn này phải ổn định kể cả khi giao ước nghiệp vụ lên v2.
    app.include_router(health.router)

    # Giao ước nghiệp vụ — có phiên bản.
    app.include_router(api_router, prefix="/v1")
    return app


app = create_app()
