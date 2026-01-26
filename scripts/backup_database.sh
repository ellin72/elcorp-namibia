"""
scripts/backup_database.sh - PostgreSQL backup script with encryption
Nightly backup with compression and encryption
"""

#!/bin/bash

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENCRYPT_PASSWORD="${BACKUP_ENCRYPTION_PASSWORD:-}"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Database configuration from environment
DB_HOST="${DATABASE_URL##*@}" # Extract host from postgresql://user:pass@host/db
DB_HOST="${DB_HOST%%/*}"
DB_NAME="${DATABASE_URL##*/}"
DB_USER="${DATABASE_URL##*//}"
DB_USER="${DB_USER%%:*}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting database backup..."

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"

# Backup database
log "Dumping database to $BACKUP_FILE..."
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"

if [ ! -f "$BACKUP_FILE" ]; then
    log "ERROR: Backup file was not created"
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Backup created successfully: $BACKUP_SIZE"

# Encrypt if password provided
if [ -n "$ENCRYPT_PASSWORD" ]; then
    log "Encrypting backup..."
    ENCRYPTED_FILE="${BACKUP_FILE}.enc"
    openssl enc -aes-256-cbc -salt -in "$BACKUP_FILE" -out "$ENCRYPTED_FILE" -k "$ENCRYPT_PASSWORD"
    rm "$BACKUP_FILE"
    BACKUP_FILE="$ENCRYPTED_FILE"
    log "Backup encrypted: $BACKUP_FILE"
fi

# Verify backup
log "Verifying backup integrity..."
if file "$BACKUP_FILE" | grep -q "gzip"; then
    log "Backup verification passed"
else
    log "WARNING: Backup file may be corrupted"
fi

# Cleanup old backups
log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "backup_*.sql.gz*" -type f -mtime +"$RETENTION_DAYS" -delete
log "Cleanup completed"

log "Backup completed successfully"
exit 0
