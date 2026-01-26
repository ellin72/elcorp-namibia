"""
scripts/restore_database.sh - PostgreSQL restore script for disaster recovery
Restores from encrypted backup with integrity checks
"""

#!/bin/bash

set -euo pipefail

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file> [encryption_password]"
    echo ""
    echo "Examples:"
    echo "  $0 /backups/backup_20260126_120000.sql.gz"
    echo "  $0 /backups/backup_20260126_120000.sql.gz.enc 'password123'"
    exit 1
fi

BACKUP_FILE="$1"
ENCRYPT_PASSWORD="${2:-}"
DB_URL="${DATABASE_URL}"

if [ -z "$DB_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable not set"
    exit 1
fi

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting database restore from $BACKUP_FILE..."

# Check backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Handle encrypted backup
TEMP_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.enc ]]; then
    if [ -z "$ENCRYPT_PASSWORD" ]; then
        echo "ERROR: Backup is encrypted but no password provided"
        exit 1
    fi
    
    log "Decrypting backup..."
    TEMP_FILE="/tmp/backup_decrypt_$$.sql.gz"
    openssl enc -d -aes-256-cbc -in "$BACKUP_FILE" -out "$TEMP_FILE" -k "$ENCRYPT_PASSWORD"
    
    if [ ! -f "$TEMP_FILE" ]; then
        echo "ERROR: Failed to decrypt backup"
        exit 1
    fi
fi

# Verify backup is gzipped
if ! file "$TEMP_FILE" | grep -q "gzip"; then
    echo "ERROR: Backup file is not gzip compressed"
    rm -f "$TEMP_FILE"
    exit 1
fi

log "Backup verification passed"

# Confirm restore (safety check)
echo ""
echo "WARNING: This will overwrite the current database!"
echo "Database: $DB_URL"
echo "Backup:   $BACKUP_FILE"
echo ""
read -p "Type 'RESTORE' to confirm: " CONFIRM

if [ "$CONFIRM" != "RESTORE" ]; then
    echo "Restore cancelled"
    rm -f "$TEMP_FILE"
    exit 0
fi

# Drop and recreate database
log "Dropping and recreating database..."
psql "$DB_URL" -c "DROP SCHEMA public CASCADE;" || true
psql "$DB_URL" -c "CREATE SCHEMA public;" || true

# Restore from backup
log "Restoring from backup..."
gunzip < "$TEMP_FILE" | psql "$DB_URL"

if [ $? -ne 0 ]; then
    echo "ERROR: Restore failed"
    rm -f "$TEMP_FILE"
    exit 1
fi

log "Database restore completed successfully"

# Cleanup temp file
rm -f "$TEMP_FILE"

# Run post-restore verification
log "Running post-restore verification..."
psql "$DB_URL" -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';"

log "Restore process completed"
exit 0
