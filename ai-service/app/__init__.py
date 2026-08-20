"""ai-service — khối AI của hệ thống. Track B sở hữu.

Bố cục theo chuẩn FastAPI production (ADR-0010):

    api/           bề mặt HTTP, không chứa logic AI
    core/          cấu hình, log, số liệu, ngoại lệ, Eureka
    db/            SQLAlchemy — schema knowledge, ai, integration
    schemas/       Pydantic DTO, là GIAO ƯỚC với java-core
    repositories/  truy cập dữ liệu
    domain/        capability của Phụ lục A — orchestrator, rag, mcp_client, scoring, clustering
    integrations/  adapter ra ngoài — java_core, llm, kafka
    workers/       tác vụ nền theo vòng đời ứng dụng

Chiều phụ thuộc CHỈ ĐI MỘT HƯỚNG:

    api -> domain -> repositories -> db
     |        |
     +--------+--> core, schemas, integrations

domain KHÔNG được import từ api. Domain không cần biết mình đang chạy sau HTTP hay sau một
consumer Kafka — đó là điều kiện để dùng lại được nó trong eval harness.
"""
