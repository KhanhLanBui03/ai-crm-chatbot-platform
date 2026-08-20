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
