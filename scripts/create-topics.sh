#!/usr/bin/env bash
# Khai báo topic TƯỜNG MINH để tái lập được, dù dev đã bật auto-create (kế hoạch mục 4.3).
# Chạy sau khi kafka đã healthy:
#   docker compose up -d kafka && bash scripts/create-topics.sh
set -euo pipefail

CONTAINER="${KAFKA_CONTAINER:-crm-kafka}"
BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9092}"
PARTITIONS="${KAFKA_PARTITIONS:-3}"
# Môi trường phát triển: một broker nên RF=1. Vận hành thật cần tối thiểu 3.
REPLICATION="${KAFKA_REPLICATION:-1}"

# Khóa phân vùng của MỌI topic là tenant_id: giữ đúng thứ tự trong phạm vi một khách hàng,
# và cho phép mở rộng bằng cách tăng số phân vùng mà không phá vỡ tính nhất quán.
#
# Danh sách 9 topic chính thức chốt theo Master Plan §2.6 và ADR-0017:
TOPICS=(
  # --- 1. Sự kiện từ java-core (CRM) sang ai-service ---
  "crm.kb.document.uploaded"   # producer: java-core   consumers: ingestion-cg (ai-service UC018/019)
  "crm.conversation.closed"    # producer: java-core   consumers: summarizer-cg (ai-service UC026)
  "crm.deal.closed"            # producer: java-core   consumers: scoring-feedback-cg (ai-service UC030)

  # --- 2. Sự kiện từ ai-service sang java-core / analytics ---
  "ai.kb.document.indexed"     # producer: ai-service  consumers: analytics-cg, notification-cg (UC019)
  "ai.lead.signal.detected"    # producer: ai-service  consumers: sales-cg (java-core UC029)
  "ai.handoff.requested"       # producer: ai-service  consumers: live-agent-cg (java-core UC022)
  "ai.tool_call.audited"       # producer: ai-service  consumers: audit-cg (java-core UC024/028)
  "ai.turn.completed"          # producer: ai-service  consumers: analytics-cg, billing-cg (UC006/039)
  "ai.dlq"                     # producer: ai-service  dead-letter queue lưu trữ thông điệp lỗi (30 ngày)

  # --- 3. Topics legacy duy trì tương thích ngược (kế hoạch mục 4.3) ---
  "crm.conversation.v1"        # producer: java-core   consumers: analytics-cg, scoring-cg
  "crm.lead.v1"                # producer: java-core   consumers: analytics-cg, notification-cg
  "crm.ai-interaction.v1"      # producer: ai-service  consumers: analytics-cg
  "crm.usage.v1"               # producer: java-core   consumers: billing-cg
  "crm.document.v1"            # producer: java-core   consumers: ingestion-cg
)

echo "Tạo topic trên ${CONTAINER} (${BOOTSTRAP})..."
for t in "${TOPICS[@]}"; do
  docker exec "$CONTAINER" kafka-topics \
    --bootstrap-server "$BOOTSTRAP" \
    --create --if-not-exists \
    --topic "$t" \
    --partitions "$PARTITIONS" \
    --replication-factor "$REPLICATION"
  echo "  ok: $t"
done

echo
echo "Danh sách topic hiện có:"
docker exec "$CONTAINER" kafka-topics --bootstrap-server "$BOOTSTRAP" --list
