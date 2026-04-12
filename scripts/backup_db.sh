#!/bin/bash
# =============================================================
# Tribus-AI — Backup do Banco de Dados
# Executa pg_dump e mantém os últimos 7 backups locais.
# Uso: bash scripts/backup_db.sh
# Cron: 0 3 * * * bash /opt/tribus-ai-light/scripts/backup_db.sh >> /opt/tribus-ai-light/backups/backup.log 2>&1
# =============================================================
#
# Expansão futura para storage externo (quando houver budget):
#   aws s3 cp "$BACKUP_FILE" "s3://tribus-ai-backups/$(basename $BACKUP_FILE)"
#   ou: rclone copy "$BACKUP_FILE" remote:tribus-ai-backups/
# =============================================================

set -e

BACKUP_DIR="/opt/tribus-ai-light/backups"
DB_CONTAINER="tribus-ai-db"
DB_USER="taxmind"
DB_NAME="taxmind_db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/tribus_${TIMESTAMP}.sql.gz"
MANTER_ULTIMOS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Iniciando backup..."

# Executar pg_dump comprimido
docker exec "$DB_CONTAINER" \
  pg_dump -U "$DB_USER" "$DB_NAME" \
  | gzip > "$BACKUP_FILE"

# Verificar integridade mínima (arquivo não vazio)
if [ ! -s "$BACKUP_FILE" ]; then
  echo "[$(date)] ERRO: Arquivo de backup vazio!" >&2
  exit 1
fi

TAMANHO=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup criado: $BACKUP_FILE ($TAMANHO)"

# Remover backups mais antigos (manter os últimos N)
TOTAL=$(ls "$BACKUP_DIR"/tribus_*.sql.gz 2>/dev/null | wc -l)
if [ "$TOTAL" -gt "$MANTER_ULTIMOS" ]; then
  REMOVER=$((TOTAL - MANTER_ULTIMOS))
  ls -t "$BACKUP_DIR"/tribus_*.sql.gz | tail -"$REMOVER" | xargs rm -f
  echo "[$(date)] $REMOVER backup(s) antigo(s) removido(s). Total mantido: $MANTER_ULTIMOS"
fi

echo "[$(date)] Backup concluído com sucesso."
