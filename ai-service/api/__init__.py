"""Bề mặt HTTP của ai-service — router FastAPI.

Đặc tả giao ước với java-core: docs/openapi/ai-service-to-java-core.yaml (hạn chốt 07/09).
Endpoint dự kiến: /v1/answer, /v1/summarize, /v1/leads/score, /v1/documents/ingest,
/health, /metrics.

Tầng này chỉ nhận request, kiểm tra đầu vào và gọi xuống orchestrator. Không chứa
logic nghiệp vụ AI.
"""
