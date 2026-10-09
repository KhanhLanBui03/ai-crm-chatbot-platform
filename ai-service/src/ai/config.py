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
    # mock: client giả trong bộ nhớ (src/ai/integrations/java_core/client.py). Ba endpoint
    # /internal/* mà UC026/UC041 cần CHƯA có ở java-core (09/10) — nháp ở
    # docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md. Có rồi thì đổi sang remote.
    java_core_mode: Literal["remote", "mock"] = "mock"
    java_core_timeout_s: float = Field(default=5.0, gt=0)
    # Bí mật dùng chung cho endpoint CHỈ java-core được gọi (DELETE /v1/ai/privacy/…). Rỗng =
    # endpoint đóng hẳn (403). Gateway mở /ai/v1/** cho mọi JWT của tenant: không có chốt này thì
    # nhân viên bất kỳ xoá được dữ liệu cá nhân mà bỏ qua bước xác minh danh tính của UC041.
    internal_api_token: str = ""

    # ── MCP: repository riêng mcp-server-mock ────────────────────────────
    mcp_server_url: str = "http://host.docker.internal:9000"
    mcp_spec_version: str = "2025-06-18"

    # ── Mô hình ngôn ngữ ─────────────────────────────────────────────────
    # Ba trường anthropic_* KHÔNG còn được đọc: từ 08/10 LLM đi qua client trung lập bên dưới
    # (ADR-0028). Giữ lại để .env cũ không vỡ và để lịch sử quyết định nhìn thấy được.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    # Mô hình rẻ cho nhánh định tuyến — thí nghiệm E10
    anthropic_router_model: str = "claude-haiku-4-5-20251001"
    # Bắt buộc bằng 0 để tái lập thí nghiệm (kế hoạch mục 8.1)
    llm_temperature: float = 0.0

    # Client LLM theo chuẩn OpenAI chat completions (src/ai/integrations/llm/). Đổi nhà cung cấp
    # là đổi bốn dòng .env, không sửa code.
    # LLM_MODE TÁCH KHỎI AI_MODE: AI_MODE=mock làm vector câu hỏi thành mock-hash-1024, mà truy hồi
    # lọc theo embedding_model ⇒ kho thật trả rỗng. Muốn nhúng thật + LLM giả (giữ hạn mức 20
    # lượt/ngày của bậc miễn phí) thì phải có hai công tắc. Mặc định mock ⇒ CI không đốt lượt nào.
    llm_mode: Literal["remote", "mock"] = "mock"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"
    # Mức suy luận thấp nhất nhà cung cấp cho phép — suy luận dài là độ trễ dài. Rỗng = không gửi.
    # Phép thử 08/10: 3.5 Flash-Lite + "minimal" trung vị 1.543 ms, 10/10 câu trong ngân sách
    # (ADR-0028). 3.8 Flash không nhận "minimal"; Flash-Lite không nhận "none".
    llm_reasoning_effort: str = "minimal"
    llm_max_tokens: int = Field(default=1024, gt=0)
    # Ngân sách chặng sinh: 2.500 ms trong tổng 4.000 ms của p95 /v1/ai/chat (§5.3). Là HẠN CHÓT
    # cho cả các lần thử lại, không phải hạn của từng lần.
    llm_timeout_s: float = Field(default=2.5, gt=0)
    # Circuit breaker: hỏng liên tiếp chừng này lượt thì mở mạch; mở chừng này giây thì thử lại.
    llm_breaker_nguong_hong: int = Field(default=3, ge=1)
    llm_breaker_thoi_gian_mo_s: float = Field(default=30.0, gt=0)
    # Giá theo 1 triệu token (VND). Bậc miễn phí = 0; bật thanh toán thì điền để cost_vnd nói thật.
    llm_gia_vao_vnd_trieu_token: float = Field(default=0.0, ge=0)
    llm_gia_ra_vnd_trieu_token: float = Field(default=0.0, ge=0)

    # ── Định tuyến ý định (UC022) ────────────────────────────────────────
    # Đường nhanh: confidence >= ngưỡng VÀ ý định thuộc nhóm đi nhanh — trả mẫu câu, 0 LLM.
    fast_path_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    # Bỏ phiếu trắng (ADR-0019 §3.3): dưới ngưỡng thì hỏi lại thay vì đoán ý khách.
    # Phải khớp ROUTER_ABSTENTION_THRESHOLD của ai-classify.
    router_abstention_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    # Đặc tả UC022: hạn chờ 1.000 ms, thử lại một lần.
    classify_timeout_s: float = Field(default=1.0, gt=0.0)
    classify_retries: int = Field(default=1, ge=0)

    # ── RAG ──────────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    retrieve_top_k: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60
    refusal_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    # Sàn liên quan theo COSINE (kế hoạch Ngày 8). Toàn tập: không đoạn nào đạt ⇒ từ chối
    # NOT_COVERED mà không gọi LLM. Từng đoạn: đoạn dưới sàn không vào lời nhắc.
    # Hiệu chỉnh 09/10 (ADR-0029): với bge-m3 trên kho đo, cosine câu có đáp án thấp nhất 0,421
    # còn câu ngoài kho cao nhất 0,650 — hai phân bố chồng nhau, mọi sàn 0–0,42 cho cùng kết quả,
    # sàn cao hơn chỉ làm mất câu đúng. Luật chọn định trước lấy số nhỏ nhất ⇒ 0. Sàn từng đoạn
    # 0,15 vẫn chặn đoạn quá xa — cơ chế còn đó cho mô hình nhúng / kho khác.
    rag_san_toan_tap: float = Field(default=0.0, ge=0.0, le=1.0)
    rag_san_tung_doan: float = Field(default=0.15, ge=0.0, le=1.0)
    # UC025 — cổng bám nguồn sau sinh: groundedness_score dưới ngưỡng ⇒ HUỶ câu trả lời, từ chối
    # LOW_CONFIDENCE. 0 = tắt cổng. Hiệu chỉnh 09/10 (ADR-0029): mọi ngưỡng > 0 làm mất 4 câu
    # trả lời đúng trên bộ vàng (groundedness là phép đo từ vựng, chấm oan câu diễn đạt lại) mà
    # không thêm câu từ chối đúng nào ⇒ TẮT. Điểm vẫn được đo và ghi cho 100% lượt.
    rag_nguong_bam_nguon: float = Field(default=0.0, ge=0.0, le=1.0)
    # UC025 luồng phụ 3.3 — lượt từ chối thứ N liên tiếp trong một hội thoại thì chuyển nhân viên.
    rag_tu_choi_lap_lai_chuyen_giao: int = Field(default=2, ge=1)
    # Số đoạn đưa vào lời nhắc.
    rag_so_doan_loi_nhac: int = Field(default=5, ge=1)
    # Xếp hạng lại — MẶC ĐỊNH TẮT (rag-eval.md). Bật khi nDCG@5 tăng ≥ 5 điểm VÀ p95 < 4 s.
    rerank_enabled: bool = False

    # ── Bộ chấm tự động — UC027 bước 6, chạy nền trong worker ─────────────
    # Chỉ chạy khi LLM_MODE=remote: giám khảo giả cho nhãn giả, làm bẩn đúng tỉ lệ cần đo.
    cham_tu_dong_bat: bool = True
    cham_tu_dong_ty_le: float = Field(default=0.05, gt=0.0, le=1.0)
    cham_tu_dong_chu_ky_s: float = Field(default=900.0, gt=0)
    cham_tu_dong_toi_da: int = Field(default=50, ge=1, le=200)
    # Giám khảo tự khai độ chắc dưới ngưỡng ⇒ không ghi (UC027 luồng phụ 6.1).
    cham_tu_dong_nguong_chac: float = Field(default=0.7, ge=0.0, le=1.0)
    # Chạy nền, không có khách chờ — hạn chót rộng hơn hẳn 2,5 s của lượt chat.
    cham_tu_dong_han_chot_s: float = Field(default=15.0, gt=0)
    # Lần quét đầu sau khi worker khởi động nhìn lại bao xa.
    cham_tu_dong_nhin_lai_s: float = Field(default=86400.0, gt=0)

    # ── Tóm tắt hội thoại — UC026, chạy nền trong worker (ADR-0032) ───────
    # Dưới chừng này tin nhắn của KHÁCH thì không tóm tắt (luồng phụ 1.1): một câu chào không đáng
    # một lượt gọi mô hình. Luật, 0 đồng — đúng thứ tự Rule → ML → LLM.
    tom_tat_so_tin_khach_toi_thieu: int = Field(default=2, ge=1)
    # Lịch sử dài hơn chừng này ký tự thì tóm tắt từng khối rồi gộp (luồng phụ 2.1). ~12.000 ký tự
    # tiếng Việt ≈ 4.000 token: còn xa cửa sổ của Flash-Lite, nhưng lời nhắc ngắn thì trả lời nhanh
    # và ít "quên giữa" hơn.
    tom_tat_ky_tu_moi_khoi: int = Field(default=12_000, ge=1_000)
    # Chạy nền, không ai chờ — hạn chót rộng như bộ chấm tự động, không phải 2,5 s của lượt chat.
    tom_tat_han_chot_s: float = Field(default=20.0, gt=0)
    tom_tat_max_tokens: int = Field(default=1024, gt=0)

    # ── Kho tệp S3 — UC018 (ADR-0022) ────────────────────────────────────
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

    # ── Nạp tài liệu — UC019 (2/2), ADR-0024 ────────────────────────────
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
    # UC026 — group riêng (docs/events/README.md): offset của tóm tắt không dính vào offset nạp.
    kafka_topic_hoi_thoai_dong: str = "crm.conversation.closed"
    kafka_consumer_group_tom_tat: str = "summarizer-cg"
    # Master Plan §2.6: "Lỗi vĩnh viễn đẩy sang ai.dlq (giữ 30 ngày)". Bộ tên topic đã
    # chốt ở ADR-0017 (quyết định 2) — tên này chỉ ai-service ghi, không ai tiêu thụ tự động.
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
