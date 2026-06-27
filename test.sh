#!/usr/bin/env bash
# Test script for libpostal-fastapi Docker image
# Usage: ./test.sh [BASE_URL]  (default: http://localhost:8001)

set -euo pipefail

BASE_URL="${1:-http://localhost:8001}"
PASSES=0
FAILURES=()

pass() { PASSES=$((PASSES + 1)); echo "  PASS: $1"; }
fail() { FAILURES+=("$1"); echo "  FAIL: $1"; }

echo "Testing server at $BASE_URL"

# Wait for server
for i in $(seq 1 10); do
    if curl -sf --max-time 5 "$BASE_URL/docs" >/dev/null 2>&1; then
        break
    fi
    [ "$i" -eq 10 ] && { echo "ERROR: Server not reachable"; exit 1; }
    sleep 2
done

# --- /parse ---
echo ""
echo "--- /parse ---"

RESP=$(curl -sf --max-time 30 "$BASE_URL/parse?address=123+Main+St+New+York+NY+10001")
[ $? -eq 0 ] && pass "status 200" || fail "status 200"

echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert isinstance(d,list)" 2>/dev/null && \
    pass "is list" || fail "is list"

echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
t=[tuple(p) for p in d]
assert any(x[1]=='house_number' for x in t), 'no house_number'
assert any(x[1] in ('road','street') for x in t), 'no road/street'
assert any(x[1]=='city' for x in t), 'no city'
assert any(x[1]=='state' for x in t), 'no state'
assert any(x[1]=='postcode' for x in t), 'no postcode'
" 2>/dev/null && pass "correct components" || fail "correct components"

# UK address with language/country
RESP=$(curl -sf --max-time 30 "$BASE_URL/parse?address=10+Downing+Street+London+SW1A+2AA+UK&language=en&country=GB")
[ ${#RESP} -gt 0 ] && pass "UK address parsed" || fail "UK address parsed"

# Canadian address with language/country
RESP=$(curl -sf --max-time 30 "$BASE_URL/parse?address=123+Ottawa+St+Toronto+ON+M5H+2N2&language=en&country=CA")
[ ${#RESP} -gt 0 ] && pass "Canadian address parsed" || fail "Canadian address parsed"

echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
t=[tuple(p) for p in d]
assert any(x[1]=='house_number' for x in t), 'no house_number'
assert any(x[1] in ('road','street') for x in t), 'no road/street'
assert any(x[1]=='city' for x in t), 'no city'
assert any(x[1]=='state' for x in t), 'no province/state'
assert any(x[1]=='postcode' for x in t), 'no postcode'
" 2>/dev/null && pass "Canadian address has correct components" || fail "Canadian address has correct components"

# Empty address
RESP=$(curl -sf --max-time 30 "$BASE_URL/parse?address=")
echo "$RESP" | python3 -c "import sys,json; assert json.load(sys.stdin)==[]" 2>/dev/null && \
    pass "empty address returns []" || fail "empty address returns []"

# --- /expand ---
echo ""
echo "--- /expand ---"

RESP=$(curl -sf --max-time 30 "$BASE_URL/expand?address=123+Main+St")
[ $? -eq 0 ] && pass "status 200" || fail "status 200"

echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
assert isinstance(d,list) and all(isinstance(x,str) for x in d), 'not list of strings'
assert len(d)>=1, 'no expansions'
assert any('street' in e.lower() for e in d), 'no street expansion'
" 2>/dev/null && pass "valid expansions" || fail "valid expansions"

# --- /expandparse ---
echo ""
echo "--- /expandparse ---"

RESP=$(curl -sf --max-time 30 "$BASE_URL/expandparse?address=123+Main+St")
[ $? -eq 0 ] && pass "status 200" || fail "status 200"

echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
assert isinstance(d,list), 'not a list'
if len(d)>0:
    assert all(isinstance(x,list) for x in d[0]), 'inner not lists'
" 2>/dev/null && pass "nested structure valid" || fail "nested structure valid"

# --- Error cases ---
echo ""
echo "--- Error cases ---"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$BASE_URL/parse?address=test&country=US")
[ "$HTTP_CODE" = "400" ] && pass "country without language returns 400" || \
    fail "country without language returns 400 (got $HTTP_CODE)"

# --- Summary ---
TOTAL=$((PASSES + ${#FAILURES[@]}))
echo ""
echo "========================================"
echo "Results: $PASSES/$TOTAL passed"
if [ ${#FAILURES[@]} -gt 0 ]; then
    echo ""
    echo "Failed tests:"
    for f in "${FAILURES[@]}"; do echo "  - $f"; done
    exit 1
else
    echo "All tests passed!"
fi
