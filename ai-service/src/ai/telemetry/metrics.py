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
