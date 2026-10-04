#!/usr/bin/env bash
# Smoke test de despliegue. Solo LEE la API: no crea ni borra nada.
# Uso: bash scripts/smoke_test.sh https://mi-tienda.up.railway.app
set -uo pipefail

BASE="${1:-http://127.0.0.1:8000}"
FAIL=0

check() { # nombre  url  [codigo_esperado]
  local name="$1" url="$2" want="${3:-200}"
  local code body
  body="$(curl -s -m 20 -w '\n%{http_code}' "$url" 2>/dev/null)"
  code="$(printf '%s' "$body" | tail -n 1)"
  body="$(printf '%s' "$body" | sed '$d')"
  if [ "$code" = "$want" ]; then
    echo "OK   [$code] $name  ->  $(printf '%s' "$body" | head -c 120)"
  else
    echo "FAIL [$code, esperaba $want] $name  ($url)"
    FAIL=1
  fi
}

echo "== Smoke test contra $BASE =="
check "health"           "$BASE/api/health"
check "productos"        "$BASE/api/productos"
check "frontend servido" "$BASE/"
check "404 en ruta inexistente" "$BASE/api/no-existe" 404

if [ "$FAIL" -eq 0 ]; then
  echo "== TODO OK =="
else
  echo "== HAY FALLOS =="
fi
exit "$FAIL"
