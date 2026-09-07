"""Ngoại lệ của tầng ứng dụng.

MẪU. Mỗi ngoại lệ ở đây ứng với một mã HTTP; tầng ``api/`` dịch chúng sang phản hồi.
Không ném ``HTTPException`` từ trong ``domain/`` — domain không được biết mình đang chạy
sau HTTP hay sau một consumer Kafka.
"""


class AiServiceError(Exception):
    """Gốc của mọi ngoại lệ do ai-service chủ động ném ra."""


class TenantContextMissingError(AiServiceError):
    """Không xác định được tenant cho request. KHÔNG được xử lý tiếp khi thiếu (ADR-0001)."""


class InsufficientGroundingError(AiServiceError):
    """Không đủ căn cứ để trả lời — chuyển sang hành vi từ chối (thí nghiệm E7)."""


class ToolCallBlockedError(AiServiceError):
    """Lớp bảo vệ chặn một lượt gọi tool. Ghi kiểm toán rồi mới ném (bề mặt T4)."""
