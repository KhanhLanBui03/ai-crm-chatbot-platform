"""Healthcheck — dùng bởi Docker Compose và Eureka.

MẪU cho một endpoint. Cố tình KHÔNG phụ thuộc tenant: healthcheck phải trả lời được cả khi
chưa có request nghiệp vụ nào.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Sống hay chết. Docker Compose gọi endpoint này."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    """Sẵn sàng nhận request chưa — kiểm tra CSDL, Kafka, mô hình đã nạp."""
    # TODO: kiểm tra kết nối Postgres, Kafka, và mô hình nhúng đã nạp xong
    return {"status": "ok"}
