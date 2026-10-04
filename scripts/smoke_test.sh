#!/usr/bin/env bash
# Smoke test de despliegue. Solo LEE la API: no crea ni borra nada.
# Uso: bash scripts/smoke_test.sh https://mi-tienda.up.railway.app
set -uo pipefail

BASE="${1:-http://127.0.0.1:8000}"
FAIL=0

check() { # nombre  url  [codigo_esperado]  [args extra para curl...]
  local name="$1" url="$2" want="${3:-200}"
  if [ "$#" -ge 3 ]; then shift 3; else shift "$#"; fi
  local code body
  body="$(curl -s -m 20 -w '\n%{http_code}' "$@" "$url" 2>/dev/null)"
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

# Assets del frontend: si estos dan 404 la pagina carga sin CSS ni JS (el 200 de
# "/" lo oculta). Son la senal temprana de un StaticFiles montado mal.
check "css"              "$BASE/static/css/styles.css"
check "js"               "$BASE/static/js/main.js"
check "imagen producto"  "$BASE/static/assets/audifonos.svg"

# Login del admin: valida SECRET_KEY + ADMIN_PASSWORD + hash de bcrypt de punta
# a punta. Un 401/500 aqui significa que el panel de admin no va a funcionar.
check "login admin"      "$BASE/api/auth/login" 200 \
  -X POST -H "Content-Type: application/json" \
  -d "{\"email\":\"${ADMIN_EMAIL:-admin@tienda.com}\",\"password\":\"${ADMIN_PASSWORD:-admin123}\"}"

if [ "$FAIL" -eq 0 ]; then
  echo "== TODO OK =="
else
  echo "== HAY FALLOS =="
fi
exit "$FAIL"
