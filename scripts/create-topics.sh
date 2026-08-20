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
TOPICS=(
  "crm.conversation.v1"    # producer: java-core   consumers: analytics-cg, scoring-cg
  "crm.lead.v1"            # producer: java-core   consumers: analytics-cg, notification-cg
  "crm.ai-interaction.v1"  # producer: ai-service  consumers: analytics-cg
  "crm.usage.v1"           # producer: java-core   consumers: billing-cg
  "crm.document.v1"        # producer: java-core   consumers: ingestion-cg (ai-service)
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
