#!/usr/bin/env bash
# Chạy dải migration V2xx của Track B (ai-service).
#
# Vì sao cần script riêng: java-core nhúng Flyway trong Spring Boot nên dải V1xx tự
# chạy lúc khởi động. ai-service là FastAPI, không có Flyway nhúng — nên dải V2xx
# chạy bằng Flyway CLI trong một container dùng một lần.
#
# BẪY QUAN TRỌNG — bảng lịch sử riêng:
#   Hai Flyway trên cùng một CSDL phải có bảng lịch sử KHÁC NHAU. Track A dùng mặc
#   định `flyway_schema_history` trong schema platform; Track B dùng
#   `flyway_schema_history_ai` trong schema knowledge. Dùng chung một bảng thì mỗi
#   lần chạy một làn, Flyway sẽ thấy migration của làn kia là "applied but missing"
#   và từ chối chạy tiếp.
#
# Cách dùng:
#   bash scripts/migrate-ai.sh            # migrate
#   bash scripts/migrate-ai.sh info       # xem trạng thái
#   bash scripts/migrate-ai.sh validate   # kiểm checksum

set -euo pipefail

CMD="${1:-migrate}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Đọc .env nếu có, giữ nguyên biến đã đặt sẵn ở môi trường.
if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a; source "$REPO_ROOT/.env"; set +a
fi

DB_NAME="${DB_NAME:-thesis_crm}"
DB_MIGRATION_USER="${DB_MIGRATION_USER:-crm_owner}"
DB_MIGRATION_PASSWORD="${DB_MIGRATION_PASSWORD:-changeme}"

# Tên mạng do Compose sinh: <name trong docker-compose.yml>_<tên mạng>
NETWORK="${COMPOSE_NETWORK:-thesis-crm-ai_crm}"

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
    echo "Không thấy mạng Docker '$NETWORK'." >&2
    echo "Chạy 'docker compose up -d postgres' trước, hoặc đặt COMPOSE_NETWORK=<tên mạng>." >&2
    exit 1
fi

echo "Flyway $CMD — dải V2xx (knowledge, ai, integration)"

docker run --rm \
    --network "$NETWORK" \
    -v "$REPO_ROOT/ai-service/migration:/flyway/sql:ro" \
    flyway/flyway:10 \
    -url="jdbc:postgresql://postgres:5432/${DB_NAME}" \
    -user="${DB_MIGRATION_USER}" \
    -password="${DB_MIGRATION_PASSWORD}" \
    -schemas=knowledge,ai,integration \
    -defaultSchema=knowledge \
    -table=flyway_schema_history_ai \
    -baselineOnMigrate=false \
    -connectRetries=10 \
    "$CMD"

if [[ "$CMD" == "migrate" ]]; then
    cat <<'EOF'

Xong dải V2xx. Còn một bước KHÔNG nằm trong Flyway:

    docker compose exec -T postgres psql -U crm_owner -d thesis_crm \
        < ai-service/scripts/create_hnsw_index.sql

Chỉ chạy SAU KHI đã nạp dữ liệu tri thức — dựng HNSW trên bảng rỗng cho chất lượng
truy hồi kém hơn hẳn.
EOF
fi
