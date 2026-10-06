#!/usr/bin/env bash
# Chạy lại các CỔNG CHẶN của job ai-service trong .github/workflows/ci.yml ở máy dev.
# Lệnh chép nguyên văn từ CI — sửa CI thì sửa cả đây. KHÔNG dừng ở cổng đầu tiên hỏng:
# chạy đủ mọi cổng rồi in bảng tổng kết, để thấy hết tình trạng một lần.
#
#     bash scripts/check_ci_gates.sh
set -uo pipefail
cd "$(dirname "$0")/.."

declare -a RESULTS=()
pass() { RESULTS+=("PASS  $1"); echo "OK: $1"; }
fail() { RESULTS+=("FAIL  $1"); echo "FAIL: $1"; }

echo "== 1. Chiều phụ thuộc import"
dep_ok=1
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.(api|worker)\b' ai-service/src/ai/ && dep_ok=0
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.worker\b' ai-service/src/api/ && dep_ok=0
grep -rnE '^[[:space:]]*(from|import)[[:space:]]+src\.api\b' ai-service/src/worker/ && dep_ok=0
[ $dep_ok = 1 ] && pass "chiều phụ thuộc import" || fail "chiều phụ thuộc import"

echo "== 2. ruff"
(cd ai-service && ruff check src tests -q) && pass "ruff" || fail "ruff"

echo "== 3. Không import sklearn trong src/"
if grep -rnE '^[[:space:]]*(from|import)[[:space:]]+sklearn\b' ai-service/src/; then
  fail "không import sklearn"
else
  pass "không import sklearn"
fi

echo "== 4. Build image ai-service:ci"
if ! docker build -q -t ai-service:ci ai-service/ >/dev/null; then
  fail "build image"
  printf '\n%s\n' "${RESULTS[@]}"; exit 1
fi
pass "build image"

echo "== 5. ai-service sạch ML runtime (onnxruntime|torch|xgboost)"
LEAK=$(docker run --rm ai-service:ci pip list --format=freeze | grep -Ei "^(onnxruntime|torch|xgboost)")
if [ -n "$LEAK" ]; then
  echo "$LEAK"; fail "sạch ML runtime"
else
  pass "sạch ML runtime"
fi

echo "== 6. Dung lượng image (< 400 MB)"
SIZE=$(docker image inspect ai-service:ci --format '{{.Size}}')
MB=$((SIZE / 1024 / 1024))
echo "ai-service:ci = ${MB} MB"
if [ "$MB" -ge 400 ]; then
  fail "dung lượng ${MB} MB >= 400 MB"
  echo "-- 15 gói lớn nhất trong image:"
  docker run --rm ai-service:ci sh -c \
    'cd "$(python -c "import site;print(site.getsitepackages()[0])")" && du -sm * 2>/dev/null | sort -rn | head -15'
else
  pass "dung lượng ${MB} MB"
fi

printf '\n== TỔNG KẾT\n'
printf '%s\n' "${RESULTS[@]}"
printf '%s\n' "${RESULTS[@]}" | grep -q '^FAIL' && exit 1 || exit 0
