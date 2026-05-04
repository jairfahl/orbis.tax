#!/bin/bash
# =============================================================
# Orbis.tax — Redeploy de Produção
# Uso: bash redeploy.sh
# =============================================================
set -e

RAIZ="$(cd "$(dirname "$0")" && pwd)"
cd "$RAIZ"

# -------------------------------------------------------
# PRE-FLIGHT CHECKS — aborta antes de qualquer mudança
# -------------------------------------------------------
echo "==> Pre-flight checks..."

# 1. .env.prod existe
if [ ! -f "$RAIZ/.env.prod" ]; then
  echo "ERRO: .env.prod não encontrado em $RAIZ"
  exit 1
fi

# 2. Variáveis obrigatórias presentes e não-vazias
check_var() {
  local val
  val=$(grep -E "^${1}=" "$RAIZ/.env.prod" | cut -d= -f2- | tr -d '"' | tr -d "'")
  if [ -z "$val" ] || [ "$val" = "CHANGE_ME" ] || [ "$val" = "placeholder" ]; then
    echo "ERRO: variável ${1} ausente ou placeholder em .env.prod"
    exit 1
  fi
}
check_var POSTGRES_PASSWORD
check_var ANTHROPIC_API_KEY
check_var JWT_SECRET
check_var API_INTERNAL_KEY

# 3. Host nginx ativo
if ! systemctl is-active --quiet nginx; then
  echo "ERRO: nginx do host não está ativo. Execute: systemctl start nginx"
  exit 1
fi

# 4. Nenhum container ocupando porta 80 ou 443
if docker ps --format '{{.Ports}}' | grep -qE '0\.0\.0\.0:(80|443)->'; then
  echo "ERRO: container docker ocupando porta 80 ou 443. Remova antes de continuar:"
  docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep -E '0\.0\.0\.0:(80|443)->'
  exit 1
fi

echo "    OK"

# -------------------------------------------------------
# DEPLOY
# -------------------------------------------------------
echo "==> Pulling latest code..."
git fetch origin main
git reset --hard origin/main

echo "==> Updating host nginx config..."
cp "$RAIZ/nginx/host-nginx-orbis.tax.conf" /etc/nginx/sites-enabled/orbis-tax
nginx -t
systemctl reload nginx
echo "    nginx reloaded OK"

echo "==> Building and restarting containers..."
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build

# -------------------------------------------------------
# POST-DEPLOY VERIFICATION
# -------------------------------------------------------
echo "==> Waiting for startup..."
sleep 15

echo "==> Verifying containers..."
CONTAINERS=("tribus-ai-api" "tribus-ai-ui" "tribus-ai-db")
for c in "${CONTAINERS[@]}"; do
  STATUS=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "missing")
  if [ "$STATUS" != "running" ]; then
    echo "ERRO: container $c não está running (status: $STATUS)"
    docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=20
    exit 1
  fi
  echo "    $c: running"
done

echo "==> Verifying API health..."
if ! curl -sf http://127.0.0.1:8020/v1/health > /dev/null; then
  echo "ERRO: API health check falhou em http://127.0.0.1:8020/v1/health"
  exit 1
fi
echo "    API: OK"

echo "==> Verifying SSL certificate..."
CERT_CN=$(openssl s_client -connect orbis.tax:443 -servername orbis.tax 2>/dev/null \
  | openssl x509 -noout -subject 2>/dev/null \
  | grep -o 'CN\s*=\s*[^,]*' | head -1)
if ! echo "$CERT_CN" | grep -q "orbis.tax"; then
  echo "AVISO: certificado pode estar incorreto: $CERT_CN"
else
  echo "    SSL: $CERT_CN OK"
fi

echo "==> Verifying external access..."
HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" https://orbis.tax/ || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
  echo "AVISO: https://orbis.tax/ retornou HTTP $HTTP_CODE"
else
  echo "    https://orbis.tax/: HTTP $HTTP_CODE OK"
fi

echo ""
echo "============================================"
echo "Deploy concluido: https://orbis.tax"
echo "============================================"
