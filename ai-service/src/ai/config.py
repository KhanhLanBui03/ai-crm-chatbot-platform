"""Cấu hình ứng dụng — nguồn sự thật duy nhất, đọc từ biến môi trường.

MẪU: mọi module khác lấy cấu hình qua ``get_settings()``, không đọc ``os.environ`` trực tiếp.
Đọc rải rác khiến không biết được ứng dụng thật sự cần biến nào, và không kiểm tra được lúc
khởi động rằng biến bắt buộc đã có.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình đọc từ ``.env`` hoặc biến môi trường của container."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Máy chủ ──────────────────────────────────────────────────────────
    ai_service_port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── CSDL: chỉ schema knowledge, ai, integration (Track B sở hữu) ──────
    # ai-service KHÔNG chạm schema nghiệp vụ của Track A (ADR-0002).
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "thesis_crm"
    db_username: str = "ai_app"
    db_password: str = "changeme"

    # ── Kafka ────────────────────────────────────────────────────────────
    kafka_bootstrap: str = "kafka:9092"
    kafka_consumer_group: str = "ingestion-cg"

    # ── Eureka ───────────────────────────────────────────────────────────
    eureka_url: str = "http://eureka-server:8761/eureka"
    eureka_app_name: str = "ai-service"

    # ── java-core: bề mặt DUY NHẤT để chạm dữ liệu nghiệp vụ ─────────────
    java_core_url: str = "http://java-core:8081"

    # ── MCP: repository riêng mcp-server-mock ────────────────────────────
    mcp_server_url: str = "http://host.docker.internal:9000"
    mcp_spec_version: str = "2025-06-18"

    # ── Mô hình ngôn ngữ ─────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    # Mô hình rẻ cho nhánh định tuyến — thí nghiệm E10
    anthropic_router_model: str = "claude-haiku-4-5-20251001"
    # Bắt buộc bằng 0 để tái lập thí nghiệm (kế hoạch mục 8.1)
    llm_temperature: float = 0.0

    # ── RAG ──────────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    retrieve_top_k: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60
    refusal_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    # ── Kho tệp S3 — UC018 (ADR-0019) ────────────────────────────────────
    # java-core GHI tệp gốc vào bucket, ai-service chỉ ĐỌC. Key có dạng {tenant_id}/… — cô lập
    # ngay ở tầng lưu trữ, không chỉ ở truy vấn. Dev: RustFS trong compose. Cloud: AWS S3
    # (s3_endpoint = "s3.amazonaws.com", s3_secure = True).
    s3_endpoint: str = "rustfs:9000"
    s3_secure: bool = False
    s3_region: str = "us-east-1"
    s3_bucket: str = "kb-tai-lieu"
    # Để trống cả hai trên cloud: client tự lấy quyền qua IAM role (IRSA), không giữ khoá.
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # 20 MiB = 20 × 1024 × 1024, khớp cách Spring hiểu "20MB" ở phía java-core. Dùng
    # 20 000 000 thì tệp nằm giữa hai con số được java-core nhận nhưng ai-service trả 413.
    # java-core chặn trước; ở đây là lớp phòng thủ thứ hai.
    kb_max_file_bytes: int = 20 * 1024 * 1024

    # ── Nạp tài liệu — UC019 ─────────────────────────────────────────────
    # Trần thời gian phân tích MỘT tệp ở tiến trình con. PDF 100 trang đo được vài giây; quá
    # trần gần như chắc chắn là tệp hỏng làm thư viện treo → giết tiến trình con, tài liệu
    # chuyển FAILED với PARSE_TIMEOUT.
    kb_parse_timeout_s: float = Field(default=120.0, gt=0)
    # Cỡ đoạn mục tiêu, tính bằng token ƯỚC LƯỢNG (xem rag/ingest/chia_doan.py).
    kb_chunk_tokens: int = Field(default=500, gt=0)

    # ── Nạp tài liệu — UC019 (2/2), ADR-0021 ────────────────────────────
    # Số đoạn mỗi lần gọi /v1/embed/batch và mỗi transaction ghi knowledge_chunks. Nhúng xong lô
    # nào ghi lô đó rồi bỏ vector khỏi bộ nhớ — tài liệu 3.000 đoạn không giữ 3.000 vector cùng lúc.
    kb_embed_batch: int = Field(default=32, gt=0, le=128)
    # Trần số lần NHẬN xử lý một tài liệu (attempt_count). Đủ trần: lỗi tạm thời → FAILED
    # INGEST_RETRY_EXHAUSTED; tiến trình chết → FAILED INGEST_STALLED.
    kb_so_luot_toi_da: int = Field(default=3, ge=1)
    # Chờ trước lượt thử thứ 2, thứ 3… khi gặp lỗi tạm thời (giây). Hết danh sách thì dùng số cuối.
    kb_cho_thu_lai_s: tuple[float, ...] = (5.0, 30.0)
    # Tài liệu PROCESSING không có nhịp tim (updated_at) quá chừng này thì coi như tiến trình đã
    # chết. Phải lớn hơn hẳn chặng dài nhất không ghi nhịp tim: phân tích một tệp, trần 120 s.
    kb_job_ket_sau_s: float = Field(default=300.0, gt=0)
    # Chu kỳ chạy bộ quét job kẹt trong worker.
    kb_chu_ky_quet_s: float = Field(default=60.0, gt=0)

    # ── Kafka — worker nạp tài liệu ─────────────────────────────────────
    kafka_topic_tai_lieu: str = "crm.kb.document.uploaded"
    # Master Plan §2.6: "Lỗi vĩnh viễn đẩy sang ai.dlq (giữ 30 ngày)". Bộ tên topic còn lại chưa
    # chốt (ADR-0017 quyết định 4) — tên này chỉ ai-service ghi, không ai tiêu thụ tự động.
    kafka_topic_dlq: str = "ai.dlq"

    # ── Tầng suy luận — §3.4.1 ──────────────────────────────────────────
    # remote: gọi ai-embed. mock: vector giả seed cố định (CI, dev khi chưa có ai-embed).
    # offline: nạp model trong tiến trình — KHÔNG hỗ trợ ở ai-service (không có ML runtime, §3.2).
    ai_mode: Literal["remote", "mock", "offline"] = "remote"
    embed_url: str = "http://ai-embed:8080"
    # Một lô 32 đoạn trên CPU: đo ở Ngày 7/15. Tạm đặt rộng; chuỗi timeout phải tăng dần từ trong
    # ra ngoài (§3.10.2) — ở đây là job nền nên không bị ALB 120 s chặn trên.
    embed_timeout_s: float = Field(default=60.0, gt=0)

    @property
    def database_url(self) -> str:
        """DSN cho SQLAlchemy async."""
        return (
            f"postgresql+psycopg://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Trả về cấu hình đã nạp, chỉ đọc một lần cho cả vòng đời tiến trình."""
    return Settings()
