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
  "crm.document.v1"        # DocumentUpdated/Deleted — chờ chốt bộ tên topic (ADR-0017 quyết định 4)
  # UC018 → UC019. Đặc tả ghi 12 phân vùng; dev dùng chung PARTITIONS như các topic khác.
  "crm.kb.document.uploaded"  # producer: java-core   consumers: ingestion-cg (ai-service)
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

# Hàng đợi chết của ai-service (Master Plan §2.6, ADR-0021). Giữ 30 ngày thay vì mặc định 7:
# đủ để sửa lỗi rồi phát lại, và khớp hạn dọn ai.processed_events — quá hạn đó không còn bản tin
# nào để nhận trùng. Khoá vẫn là tenant_id (giữ nguyên khoá của bản tin gốc).
DLQ_RETENTION_MS=$((30 * 24 * 60 * 60 * 1000))
docker exec "$CONTAINER" kafka-topics \
  --bootstrap-server "$BOOTSTRAP" \
  --create --if-not-exists \
  --topic "ai.dlq" \
  --partitions "$PARTITIONS" \
  --replication-factor "$REPLICATION" \
  --config "retention.ms=$DLQ_RETENTION_MS"
echo "  ok: ai.dlq (giữ 30 ngày)"

echo
echo "Danh sách topic hiện có:"
docker exec "$CONTAINER" kafka-topics --bootstrap-server "$BOOTSTRAP" --list
