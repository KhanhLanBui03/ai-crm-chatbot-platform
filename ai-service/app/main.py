"""Điểm vào của ai-service — factory tạo ứng dụng FastAPI.

MẪU. Dùng factory ``create_app()`` thay vì tạo ``app`` ở cấp module để kiểm thử dựng được
nhiều bản ứng dụng với cấu hình khác nhau mà không đụng biến toàn cục.

Vòng đời (``lifespan``) là chỗ duy nhất được phép khởi động và tắt tài nguyên nền:
Eureka và consumer Kafka. Kế hoạch mục 4.3 nói rõ — consumer chạy trong tác vụ nền theo
vòng đời ứng dụng, KHÔNG chạy trong luồng xử lý request.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core import eureka
from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Khởi động và tắt tài nguyên nền."""
    settings = get_settings()

    await eureka.register(settings)
    # TODO: khởi động consumer Kafka (ingestion-cg) như một asyncio task nền.
    #       enable.auto.commit = False; xác nhận offset SAU KHI xử lý xong (mục 4.3).
    # TODO: nạp mô hình nhúng và mô hình xếp hạng lại — chậm, phải làm ở đây chứ không
    #       làm lúc phục vụ request đầu tiên.

    logger.info("ai-service đã khởi động")
    try:
        yield
    finally:
        # TODO: dừng consumer Kafka, chờ xử lý nốt bản tin đang dở
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
    # TODO: exception handler dịch AiServiceError sang phản hồi HTTP
    # TODO: /metrics cho Prometheus (prometheus-client)

    # Bề mặt vận hành — KHÔNG đánh phiên bản. Docker Compose gọi /health, Prometheus gọi
    # /metrics; hai đường dẫn này phải ổn định kể cả khi giao ước nghiệp vụ lên v2.
    app.include_router(health.router)

    # Giao ước nghiệp vụ — có phiên bản.
    app.include_router(api_router, prefix="/v1")
    return app


app = create_app()
