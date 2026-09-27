#!/usr/bin/env bash
# UC018 đầu-cuối trên hạ tầng DÙNG MỘT LẦN — minh chứng cổng ra Ngày 3.
#
#   scripts/e2e-uc018.sh up     # dựng Postgres + RustFS + Kafka, chạy ai-service và java-core
#   scripts/e2e-uc018.sh run    # đóng vai người dùng tải tệp, rồi soi từng trường ở CSDL, S3, Kafka
#   scripts/e2e-uc018.sh soi    # chạy LẠI riêng phần soi dữ liệu (kiểm ngược: phá dữ liệu rồi soi)
#   scripts/e2e-uc018.sh down   # dừng tiến trình, xoá container — không để lại gì
#
# Giữa `run` và `down`: chụp ảnh key có tenant_id ở giao diện RustFS http://localhost:59011
# (đăng nhập kb-e2e / kb-e2e-secret → bucket kb-tai-lieu).
#
# Mọi cổng ở dải 5xxxx để không đụng stack docker compose đang chạy (5432, 9010, 29092, 8000,
# 8081). KHÔNG chạm CSDL dev: Postgres ở đây là container riêng, xoá khi `down`.
#
# Cần: Docker, ai-service/.venv (httpx), JDK 21 + Maven.
set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
STATE="${TMPDIR:-/tmp}/uc018-e2e"
NET=uc018-e2e
PG=uc018-e2e-pg; S3=uc018-e2e-s3; ZK=uc018-e2e-zk; KAFKA=uc018-e2e-kafka
PG_PORT=55432; S3_PORT=59010; S3_UI_PORT=59011; KAFKA_PORT=59092; AI_PORT=58000; CORE_PORT=58081
S3_KEY=kb-e2e; S3_SECRET=kb-e2e-secret; BUCKET=kb-tai-lieu
TENANT_A=11111111-1111-1111-1111-111111111111
TENANT_B=22222222-2222-2222-2222-222222222222

cho() {  # cho <mô tả> <số giây> <lệnh…> — chờ tới khi lệnh thành công
    local mo_ta="$1" han="$2"; shift 2
    for _ in $(seq 1 "$han"); do "$@" >/dev/null 2>&1 && return 0; sleep 1; done
    echo "Quá ${han}s mà $mo_ta chưa sẵn sàng — xem log ở $STATE" >&2; exit 1
}

psql_e2e() { docker exec -i "$PG" psql -q -U crm_owner -d thesis_crm -v ON_ERROR_STOP=1 "$@"; }

cmd_up() {
    mkdir -p "$STATE"
    docker network create "$NET" >/dev/null
    docker run -d --name "$PG" --network "$NET" -p "$PG_PORT:5432" \
        -e POSTGRES_DB=thesis_crm -e POSTGRES_USER=crm_owner -e POSTGRES_PASSWORD=changeme \
        -v "$ROOT/scripts/init-db.sql:/docker-entrypoint-initdb.d/00-init.sql:ro" \
        pgvector/pgvector:pg16 >/dev/null
    docker run -d --name "$S3" --network "$NET" -p "$S3_PORT:9000" -p "$S3_UI_PORT:9001" \
        -e RUSTFS_ACCESS_KEY="$S3_KEY" -e RUSTFS_SECRET_KEY="$S3_SECRET" -e RUSTFS_CONSOLE_ENABLE=true \
        rustfs/rustfs:1.0.0 >/dev/null
    # Kafka chế độ ZooKeeper, hai listener — cùng cấu hình với docker-compose.yml (ADR-0009).
    docker run -d --name "$ZK" --network "$NET" -e ZOOKEEPER_CLIENT_PORT=2181 \
        confluentinc/cp-zookeeper:7.9.0 >/dev/null
    docker run -d --name "$KAFKA" --network "$NET" -p "$KAFKA_PORT:$KAFKA_PORT" \
        -e KAFKA_BROKER_ID=1 -e KAFKA_ZOOKEEPER_CONNECT="$ZK:2181" \
        -e KAFKA_LISTENERS="INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:$KAFKA_PORT" \
        -e KAFKA_ADVERTISED_LISTENERS="INTERNAL://$KAFKA:9092,EXTERNAL://localhost:$KAFKA_PORT" \
        -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT \
        -e KAFKA_INTER_BROKER_LISTENER_NAME=INTERNAL -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
        -e KAFKA_NUM_PARTITIONS=3 confluentinc/cp-kafka:7.9.0 >/dev/null

    cho "Postgres" 60 docker exec "$PG" pg_isready -U crm_owner -d thesis_crm
    sleep 2  # initdb khởi động lại một lần sau khi chạy init-db.sql
    cho "Postgres" 30 docker exec "$PG" psql -U crm_owner -d thesis_crm -c "select 1"
    cho "RustFS" 60 curl -fsS "http://localhost:$S3_PORT/health"
    curl -fsS --aws-sigv4 "aws:amz:us-east-1:s3" --user "$S3_KEY:$S3_SECRET" \
        -X PUT "http://localhost:$S3_PORT/$BUCKET" >/dev/null
    for f in "$ROOT"/ai-service/migration/V2*.sql; do psql_e2e < "$f" >/dev/null; done
    cho "Kafka" 90 docker exec "$KAFKA" kafka-topics --bootstrap-server localhost:9092 --list
    docker exec "$KAFKA" kafka-topics --bootstrap-server localhost:9092 --create \
        --topic crm.document.v1 --partitions 3 --replication-factor 1 >/dev/null

    echo "Dựng ai-service (:$AI_PORT)…"
    # `exec` trong subshell: tiến trình nền CHÍNH LÀ python, nên $! là PID của ai-service. Viết
    # `(cd … && python … &)` thì `&` áp lên cả chuỗi — $! thành PID của một bash trung gian, `down`
    # giết nhầm nó và python sống sót (đã gặp khi viết script này).
    (cd "$ROOT/ai-service" && exec env RUN_MODE=api PORT="$AI_PORT" DB_HOST=localhost DB_PORT="$PG_PORT" \
        DB_USERNAME=ai_app DB_PASSWORD=changeme S3_ENDPOINT="localhost:$S3_PORT" S3_SECURE=false \
        S3_BUCKET="$BUCKET" S3_ACCESS_KEY="$S3_KEY" S3_SECRET_KEY="$S3_SECRET" AI_MODE=mock \
        .venv/bin/python -m src.entrypoint) >"$STATE/ai-service.log" 2>&1 &
    echo $! >"$STATE/ai-service.pid"

    echo "Đóng gói và dựng java-core (:$CORE_PORT)…"
    mvn -q -B -ntp -f "$ROOT/java-core/pom.xml" -DskipTests package
    DEV_JWT_DIR="$STATE/jwt" "$ROOT/scripts/dev-jwt.sh" "$TENANT_A" >/dev/null 2>&1
    SERVER_PORT="$CORE_PORT" DB_HOST=localhost DB_PORT="$PG_PORT" DB_USERNAME=crm_app DB_PASSWORD=changeme \
        DB_MIGRATION_USER=crm_owner DB_MIGRATION_PASSWORD=changeme \
        S3_ENDPOINT="localhost:$S3_PORT" S3_ACCESS_KEY="$S3_KEY" S3_SECRET_KEY="$S3_SECRET" \
        AI_SERVICE_URL="http://localhost:$AI_PORT" KAFKA_BOOTSTRAP="localhost:$KAFKA_PORT" \
        JWT_PUBLIC_KEY_LOCATION="file:$STATE/jwt/dev-public.pem" EUREKA_CLIENT_ENABLED=false REDIS_HOST=localhost \
        nohup java -jar "$ROOT"/java-core/target/java-core-*.jar >"$STATE/java-core.log" 2>&1 &
    echo $! >"$STATE/java-core.pid"

    cho "ai-service" 60 curl -fsS "http://localhost:$AI_PORT/health"
    cho "java-core" 120 curl -fsS "http://localhost:$CORE_PORT/actuator/health/liveness"

    # Hai tenant: A gói STARTER (100) cho 25 tệp mẫu, B gói TRIAL (20) để chạm trần.
    psql_e2e <<SQL
INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES
  ('$TENANT_A', 'E2E A', 'e2e-a', 'a@example.test'), ('$TENANT_B', 'E2E B', 'e2e-b', 'b@example.test');
INSERT INTO platform.tenant_subscriptions (tenant_id, plan_id, status, period_start, period_end)
SELECT v.t, p.id, 'ACTIVE', now() - interval '1 day', now() + interval '29 days'
  FROM (VALUES ('$TENANT_A'::uuid, 'STARTER'), ('$TENANT_B'::uuid, 'TRIAL')) AS v(t, code)
  JOIN platform.subscription_plans p ON p.code = v.code;
SQL
    echo "Sẵn sàng. Tiếp: scripts/e2e-uc018.sh run"
}

cmd_run() {
    local loi=0
    # Phần 3 của e2e_uc018.py soi CSDL bằng crm_owner (bỏ qua RLS) — góc nhìn kiểm tra, không
    # phải đường đi của ứng dụng.
    E2E_JAVA_CORE_URL="http://localhost:$CORE_PORT" DEV_JWT_DIR="$STATE/jwt" \
        E2E_DB_DSN="postgresql://crm_owner:changeme@localhost:$PG_PORT/thesis_crm" \
        E2E_S3_ENDPOINT="localhost:$S3_PORT" E2E_S3_ACCESS="$S3_KEY" E2E_S3_SECRET="$S3_SECRET" \
        E2E_BUCKET="$BUCKET" E2E_KAFKA="localhost:$KAFKA_PORT" E2E_STATE="$STATE" \
        "$ROOT/ai-service/.venv/bin/python" "$ROOT/scripts/e2e_uc018.py" || loi=1

    # Job phát outbox chạy mỗi 500 ms — chờ nó xả hết trước khi soi Kafka.
    cho "job phát outbox" 30 bash -c "[ \"\$(docker exec $PG psql -U crm_owner -d thesis_crm -tAc \
        'select count(*) from platform.outbox_events where published_at is null')\" = 0 ]"

    echo "### 3. Trạng thái sau cùng"
    echo
    echo '```'
    docker exec "$PG" psql -U crm_owner -d thesis_crm -c "
        SELECT t.slug, u.metric, u.used_value AS used, u.quota_value AS quota,
               u.warned_at IS NOT NULL AS warned, u.blocked_at IS NOT NULL AS blocked
          FROM platform.usage_records u JOIN platform.tenants t ON t.id = u.tenant_id ORDER BY 1, 2" \
        -c "SELECT tenant_id, count(*) AS su_kien, count(published_at) AS da_phat
              FROM platform.outbox_events GROUP BY 1 ORDER BY 1" \
        -c "SELECT version, source_type, file_path FROM knowledge.knowledge_documents
             WHERE title = 'Chính sách đổi trả' ORDER BY version"
    echo "Object trên S3 theo thư mục tenant:"
    curl -fsS --aws-sigv4 "aws:amz:us-east-1:s3" --user "$S3_KEY:$S3_SECRET" \
        "http://localhost:$S3_PORT/$BUCKET?list-type=2&max-keys=1000" \
        | grep -o "<Key>[^<]*</Key>" | sed 's/<[^>]*>//g' | cut -d/ -f1 | sort | uniq -c
    echo "Kafka crm.document.v1 — số bản tin theo (khoá, phân vùng):"
    docker exec "$KAFKA" kafka-console-consumer --bootstrap-server localhost:9092 \
        --topic crm.document.v1 --from-beginning --timeout-ms 10000 \
        --property print.key=true --property print.partition=true --property key.separator='|' 2>/dev/null \
        | awk -F'|' '{print $2, $1}' | sort | uniq -c
    echo "Một bản tin mẫu (header | khoá | giá trị):"
    docker exec "$KAFKA" kafka-console-consumer --bootstrap-server localhost:9092 \
        --topic crm.document.v1 --from-beginning --max-messages 1 --timeout-ms 10000 \
        --property print.headers=true --property print.key=true --property key.separator=' | ' 2>/dev/null
    echo '```'
    echo
    echo "Chụp ảnh key có tenant_id: http://localhost:$S3_UI_PORT ($S3_KEY / $S3_SECRET) → $BUCKET"
    return $loi
}

cmd_soi() {
    E2E_JAVA_CORE_URL="http://localhost:$CORE_PORT" DEV_JWT_DIR="$STATE/jwt" \
        E2E_DB_DSN="postgresql://crm_owner:changeme@localhost:$PG_PORT/thesis_crm" \
        E2E_S3_ENDPOINT="localhost:$S3_PORT" E2E_S3_ACCESS="$S3_KEY" E2E_S3_SECRET="$S3_SECRET" \
        E2E_BUCKET="$BUCKET" E2E_KAFKA="localhost:$KAFKA_PORT" E2E_STATE="$STATE" \
        "$ROOT/ai-service/.venv/bin/python" "$ROOT/scripts/e2e_uc018.py" --chi-soi
}

cmd_down() {
    for p in java-core ai-service; do
        [[ -f "$STATE/$p.pid" ]] && kill "$(cat "$STATE/$p.pid")" 2>/dev/null || true
    done
    docker rm -f "$PG" "$S3" "$KAFKA" "$ZK" >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
    rm -rf "$STATE"
    echo "Đã dọn sạch hạ tầng e2e."
}

case "${1:-}" in
    up) cmd_up ;;
    run) cmd_run ;;
    soi) cmd_soi ;;
    down) cmd_down ;;
    *) sed -n '2,14p' "$0" >&2; exit 2 ;;
esac
