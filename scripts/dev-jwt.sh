#!/usr/bin/env bash
# Sinh cặp khoá RS256 cho môi trường DEV (nếu chưa có) và in một JWT để gọi thử java-core.
#
#   scripts/dev-jwt.sh <tenant_id> [user_id] [role_code] [ttl_giay]
#   TOKEN=$(scripts/dev-jwt.sh 11111111-1111-1111-1111-111111111111)
#   curl -H "Authorization: Bearer $TOKEN" -F file=@data/kb_samples/faq-thanh-toan.txt \
#        -F title="Câu hỏi thường gặp" http://localhost:8081/api/v1/documents
#
# CHỈ DÙNG Ở DEV. Luồng phát hành token thật (UC002, /api/v1/auth/login) chưa có; đến lúc đó
# java-core ký bằng khoá của chính nó và script này hết việc.
#
# Khoá nằm ở .secrets/jwt/ (đã .gitignore). java-core đọc khoá CÔNG KHAI qua biến
# JWT_PUBLIC_KEY_LOCATION — script in sẵn giá trị cần đặt ra stderr.
#
# Claim theo securitySchemes.tenantJwt của docs/openapi/dashboard-api.yaml:
# sub (userId) · tenantId · roleCode.
set -euo pipefail

UUID_RE='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

if [[ $# -lt 1 ]]; then
    sed -n '2,8p' "$0" >&2
    exit 2
fi

TENANT_ID="$1"
USER_ID="${2:-00000000-0000-0000-0000-00000000a001}"
ROLE_CODE="${3:-TENANT_ADMIN}"
TTL="${4:-3600}"

# java-core chỉ nhận UUID dạng chuẩn chữ thường — kiểm ở đây để lỗi hiện ngay, không phải 401 câm.
for v in "$TENANT_ID" "$USER_ID"; do
    [[ "$v" =~ $UUID_RE ]] || { echo "Không phải UUID chữ thường dạng chuẩn: $v" >&2; exit 2; }
done

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
DIR="${DEV_JWT_DIR:-$ROOT/.secrets/jwt}"
PRIV="$DIR/dev-private.pem"
PUB="$DIR/dev-public.pem"

if [[ ! -f "$PRIV" ]]; then
    mkdir -p "$DIR"
    chmod 700 "$DIR"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$PRIV" 2>/dev/null
    chmod 600 "$PRIV"
    openssl pkey -in "$PRIV" -pubout -out "$PUB"
    echo "Đã sinh cặp khoá dev ở $DIR" >&2
fi

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }

NOW=$(date +%s)
HEADER='{"alg":"RS256","typ":"JWT"}'
PAYLOAD=$(printf '{"sub":"%s","tenantId":"%s","roleCode":"%s","iat":%d,"exp":%d}' \
    "$USER_ID" "$TENANT_ID" "$ROLE_CODE" "$NOW" "$((NOW + TTL))")

H=$(printf '%s' "$HEADER" | b64url)
P=$(printf '%s' "$PAYLOAD" | b64url)
S=$(printf '%s.%s' "$H" "$P" | openssl dgst -sha256 -sign "$PRIV" -binary | b64url)

cat >&2 <<EOF
java-core cần:  JWT_PUBLIC_KEY_LOCATION=file:$PUB
(trong docker compose: JWT_PUBLIC_KEY_LOCATION=file:/run/secrets/jwt/dev-public.pem)
EOF
printf '%s.%s.%s\n' "$H" "$P" "$S"
