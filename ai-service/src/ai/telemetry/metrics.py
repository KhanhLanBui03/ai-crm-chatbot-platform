"""Số liệu Prometheus — kế hoạch mục 4.5.

MẪU. Bốn chỉ số tối thiểu bắt buộc phải có: độ trễ theo từng chặng, số lượt gọi mô hình
ngôn ngữ, tỉ lệ lỗi tool, độ trễ tiêu thụ Kafka.

Lưu ý: KHÔNG đặt tenant_id làm nhãn. Số tenant tăng thì số chuỗi thời gian nổ theo — đây là
lỗi kinh điển làm sập Prometheus.
"""

from prometheus_client import Counter, Histogram

rag_stage_latency = Histogram(
    "ai_rag_stage_latency_seconds",
    "Độ trễ theo từng chặng của đường ống RAG",
    labelnames=("stage",),  # ingest | retrieve | rerank | generate | verify
)

llm_calls = Counter(
    "ai_llm_calls_total",
    "Số lượt gọi mô hình ngôn ngữ",
    labelnames=("model", "route", "outcome"),
)

# KPI §1.6 ">= 55% lượt không gọi LLM" = sum(llm_called="false") / sum(tất cả)
chat_turns = Counter(
    "ai_chat_turns_total",
    "Số lượt /v1/ai/chat theo nhánh xử lý",
    labelnames=("branch", "llm_called"),  # branch: 7 giá trị V204 · llm_called: true|false
)

tool_calls = Counter(
    "ai_tool_calls_total",
    "Số lượt gọi tool qua MCP",
    labelnames=("tool_name", "result_status"),
)

kafka_consume_latency = Histogram(
    "ai_kafka_consume_latency_seconds",
    "Độ trễ từ lúc sự kiện được phát tới lúc xử lý xong",
    labelnames=("topic",),
)

# UC022 bước 9 (Ngày 10): ghi ai.ai_interactions hỏng thì lượt chat vẫn trả lời — số này là
# cách DUY NHẤT biết telemetry đang mất dòng. Khác 0 nghĩa là báo cáo UC039/UC027 thiếu số liệu.
turn_record_failures = Counter(
    "ai_turn_record_failures_total",
    "Số lượt chat không ghi được vào ai.ai_interactions",
)

# UC025 — số lượt từ chối theo lý do (4 giá trị V204). Nhãn hữu hạn, không có tenant.
refusals = Counter(
    "ai_refusals_total",
    "Số lượt nhánh tri thức từ chối trả lời",
    labelnames=("reason",),
)

# UC027 — bộ chấm tự động: chấm xong / bỏ vì không chắc / hỏng.
auto_eval = Counter(
    "ai_auto_eval_total",
    "Số lượt bộ chấm tự động đã xử lý",
    labelnames=("outcome",),  # GHI | KHONG_CHAC | BO_QUA | LOI
)

# UC026 — kết cục từng lượt tóm tắt. SAI_DINH_DANG khác 0 kéo dài = lời nhắc cần sửa.
summaries = Counter(
    "ai_summaries_total",
    "Số lượt tóm tắt hội thoại theo kết cục",
    labelnames=("trigger", "outcome"),  # outcome: DA_GHI | BO_QUA_NGAN | TRUNG | SAI_DINH_DANG
)

# UC041 — số dòng đã xoá theo bảng. Không có contact_id/tenant làm nhãn (lý do ở đầu tệp).
privacy_erasures = Counter(
    "ai_privacy_erased_rows_total",
    "Số dòng dữ liệu cá nhân đã xoá theo bảng",
    labelnames=("table",),
)
