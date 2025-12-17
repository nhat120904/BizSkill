#!/bin/bash

# ===========================================
# BizSkill - Restore Script
# Run this on the NEW server after copying backup
# ===========================================

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore_data.sh <backup_directory>"
    echo "Example: ./restore_data.sh ./backups/20250118_143000"
    exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "🔄 Starting restore from $BACKUP_DIR..."

# Check if containers are running
if ! docker ps | grep -q bizskill-postgres; then
    echo "❌ Containers not running. Start them first with: docker-compose up -d postgres redis qdrant"
    exit 1
fi

# 1. Restore PostgreSQL
echo "📦 Restoring PostgreSQL..."
docker cp "$BACKUP_DIR/postgres_backup.dump" bizskill-postgres:/tmp/postgres_backup.dump

# Drop and recreate database
docker exec bizskill-postgres psql -U bizskill -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'bizskill' AND pid <> pg_backend_pid();" 2>/dev/null || true
docker exec bizskill-postgres psql -U bizskill -d postgres -c "DROP DATABASE IF EXISTS bizskill;"
docker exec bizskill-postgres psql -U bizskill -d postgres -c "CREATE DATABASE bizskill;"

# Restore from backup
docker exec bizskill-postgres pg_restore -U bizskill -d bizskill -c --if-exists /tmp/postgres_backup.dump 2>/dev/null || true
docker exec bizskill-postgres rm /tmp/postgres_backup.dump
echo "✅ PostgreSQL restored"

# 2. Restore Redis
echo "📦 Restoring Redis..."
if [ -f "$BACKUP_DIR/redis_dump.rdb" ]; then
    docker exec bizskill-redis redis-cli SHUTDOWN NOSAVE 2>/dev/null || true
    sleep 2
    docker cp "$BACKUP_DIR/redis_dump.rdb" bizskill-redis:/data/dump.rdb
    docker-compose restart redis
    sleep 3
    echo "✅ Redis restored"
else
    echo "⚠️  No Redis backup found, skipping..."
fi

# 3. Restore Qdrant
echo "📦 Restoring Qdrant..."
if [ -f "$BACKUP_DIR/qdrant_data.tar.gz" ]; then
    # Stop qdrant first
    docker-compose stop qdrant
    
    # Clear existing data and restore
    docker run --rm -v bizskill_qdrant_data:/target -v "$(pwd)/$BACKUP_DIR":/backup alpine sh -c "rm -rf /target/* && tar xzf /backup/qdrant_data.tar.gz -C /target"
    
    # Restart qdrant
    docker-compose start qdrant
    sleep 5
    echo "✅ Qdrant restored"
else
    echo "⚠️  No Qdrant backup found, skipping..."
fi

echo ""
echo "=========================================="
echo "✅ Restore completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart all services: docker-compose up -d"
echo "2. Check logs: docker-compose logs -f"
echo "3. Test the application"
