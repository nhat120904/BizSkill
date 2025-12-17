#!/bin/bash

# ===========================================
# BizSkill - Backup Script
# ===========================================

set -e

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting backup to $BACKUP_DIR..."

# 1. Backup PostgreSQL
echo "📦 Backing up PostgreSQL..."
docker exec bizskill-postgres pg_dump -U bizskill -d bizskill -F c -f /tmp/postgres_backup.dump
docker cp bizskill-postgres:/tmp/postgres_backup.dump "$BACKUP_DIR/postgres_backup.dump"
docker exec bizskill-postgres rm /tmp/postgres_backup.dump
echo "✅ PostgreSQL backup completed"

# 2. Backup Redis (RDB snapshot)
echo "📦 Backing up Redis..."
docker exec bizskill-redis redis-cli BGSAVE
sleep 2  # Wait for save to complete
docker cp bizskill-redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb" 2>/dev/null || echo "⚠️  No Redis dump.rdb found (may be empty)"
echo "✅ Redis backup completed"

# 3. Backup Qdrant
echo "📦 Backing up Qdrant..."
# Create snapshot for all collections
COLLECTIONS=$(docker exec bizskill-qdrant curl -s http://localhost:6333/collections | jq -r '.result.collections[].name')
for collection in $COLLECTIONS; do
    echo "  - Snapshotting collection: $collection"
    docker exec bizskill-qdrant curl -s -X POST "http://localhost:6333/collections/$collection/snapshots"
done

# Copy Qdrant storage directory
docker run --rm -v bizskill_qdrant_data:/source -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/qdrant_data.tar.gz -C /source .
echo "✅ Qdrant backup completed"

# 4. Backup environment file if exists
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/.env"
    echo "✅ .env file backed up"
fi

# 5. Create archive
echo "📦 Creating final archive..."
cd backups
tar czf "backup_$(date +%Y%m%d_%H%M%S).tar.gz" "$(basename $BACKUP_DIR)"
echo "✅ Archive created"

echo ""
echo "=========================================="
echo "✅ Backup completed successfully!"
echo "📁 Backup location: $BACKUP_DIR"
echo "=========================================="
echo ""
echo "Files created:"
ls -la "$BACKUP_DIR"
