#!/usr/bin/env bash
# Smoke test API public. Dùng: bash smoke_test.sh https://api.example.com
set -u
BASE="${1:?Cần URL gốc của API, ví dụ https://api.example.com}"
FAIL=0

check() { # $1 tên, $2 điều kiện (0 = đạt)
  if [ "$2" -eq 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; FAIL=1; fi
}

code=$(curl -s -o /tmp/smoke_health.json -w '%{http_code}' --max-time 10 "$BASE/health")
[ "$code" = "200" ]; check "GET /health → 200 (nhận $code)" $?

analyze() { # $1 text → in ra "risk_level thời_gian"
  local body; body=$(jq -n --arg t "$1" '{text:$t}')
  curl -s -o /tmp/smoke_analyze.json -w '%{time_total}' --max-time 20 \
    -H 'Content-Type: application/json' -d "$body" "$BASE/v1/analyze" > /tmp/smoke_time.txt
  echo "$(jq -r '.risk_level // "error"' /tmp/smoke_analyze.json 2>/dev/null) $(cat /tmp/smoke_time.txt)"
}

read -r lvl t <<<"$(analyze 'Tôi là cán bộ công an, anh chuyển tiền vào tài khoản tạm giữ để xác minh, không được nói với ai.')"
[ "$lvl" = "high" ]; check "Tin lừa đảo → high (nhận $lvl, ${t}s)" $?
awk "BEGIN{exit !($t < 8)}"; check "Độ trễ < 8s (${t}s)" $?

read -r lvl t <<<"$(analyze 'Mẹ ơi tối con về ăn cơm nhé.')"
[ "$lvl" = "low" ]; check "Tin bình thường → low (nhận $lvl, ${t}s)" $?

if [ $FAIL -eq 0 ]; then echo "SMOKE: ĐẠT"; else echo "SMOKE: CHƯA ĐẠT"; fi
exit $FAIL
