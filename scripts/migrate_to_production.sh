#!/bin/bash

# ===========================================
# BizSkill - Migration Script (Local to Production)
# ===========================================
# This script creates a complete backup package ready to transfer to production

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MIGRATION_DIR="./migration_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$MIGRATION_DIR"

echo -e "${BLUE}=========================================="
echo "🚀 BizSkill Data Migration - Export"
echo -e "==========================================${NC}"
echo ""

# 1. Backup PostgreSQL
echo -e "${YELLOW}📦 [1/4] Backing up PostgreSQL...${NC}"
docker exec bizskill-postgres pg_dump -U bizskill -d bizskill -F c -f /tmp/postgres_backup.dump
docker cp bizskill-postgres:/tmp/postgres_backup.dump "$MIGRATION_DIR/postgres_backup.dump"
docker exec bizskill-postgres rm /tmp/postgres_backup.dump
echo -e "${GREEN}✅ PostgreSQL backup completed${NC}"

# 2. Backup Redis
echo -e "${YELLOW}📦 [2/4] Backing up Redis...${NC}"
docker exec bizskill-redis redis-cli BGSAVE
sleep 3
docker cp bizskill-redis:/data/dump.rdb "$MIGRATION_DIR/redis_dump.rdb" 2>/dev/null || echo -e "${YELLOW}⚠️  No Redis data found (empty)${NC}"
echo -e "${GREEN}✅ Redis backup completed${NC}"

# 3. Backup Qdrant vector database
echo -e "${YELLOW}📦 [3/4] Backing up Qdrant vector database...${NC}"
docker run --rm \
    -v bizskill_qdrant_data:/source:ro \
    -v "$(pwd)/$MIGRATION_DIR":/backup \
    alpine tar czf /backup/qdrant_data.tar.gz -C /source .
echo -e "${GREEN}✅ Qdrant backup completed${NC}"

# 4. Backup HuggingFace cache (ML models) - Optional
echo -e "${YELLOW}📦 [4/4] Backing up ML model cache...${NC}"
if docker volume inspect bizskill_huggingface_cache &>/dev/null; then
    docker run --rm \
        -v bizskill_huggingface_cache:/source:ro \
        -v "$(pwd)/$MIGRATION_DIR":/backup \
        alpine tar czf /backup/huggingface_cache.tar.gz -C /source . 2>/dev/null || echo -e "${YELLOW}⚠️  No HuggingFace cache found${NC}"
    echo -e "${GREEN}✅ ML model cache backup completed${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping HuggingFace cache (will be re-downloaded on server)${NC}"
fi

# Create restore script
cat > "$MIGRATION_DIR/restore.sh" << 'RESTORE_SCRIPT'
#!/bin/bash

# ===========================================
# BizSkill - Restore Script (Run on Production Server)
# ===========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}=========================================="
echo "🔄 BizSkill Data Migration - Import"
echo -e "==========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/postgres_backup.dump" ]; then
    echo -e "${RED}Error: postgres_backup.dump not found!${NC}"
    exit 1
fi

# Load production environment
if [ -f "../.env.production" ]; then
    export $(grep -v '^#' ../.env.production | xargs)
fi

# 1. Restore PostgreSQL
echo -e "${YELLOW}📦 [1/4] Restoring PostgreSQL...${NC}"
docker cp "$SCRIPT_DIR/postgres_backup.dump" bizskill-postgres:/tmp/postgres_backup.dump

# Drop and recreate database
docker exec bizskill-postgres psql -U ${POSTGRES_USER:-bizskill} -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB:-bizskill}' AND pid <> pg_backend_pid();" postgres 2>/dev/null || true
docker exec bizskill-postgres dropdb -U ${POSTGRES_USER:-bizskill} --if-exists ${POSTGRES_DB:-bizskill}
docker exec bizskill-postgres createdb -U ${POSTGRES_USER:-bizskill} ${POSTGRES_DB:-bizskill}

# Restore data
docker exec bizskill-postgres pg_restore -U ${POSTGRES_USER:-bizskill} -d ${POSTGRES_DB:-bizskill} --no-owner --no-acl /tmp/postgres_backup.dump || echo -e "${YELLOW}⚠️  Some warnings during restore (usually safe to ignore)${NC}"
docker exec bizskill-postgres rm /tmp/postgres_backup.dump
echo -e "${GREEN}✅ PostgreSQL restored${NC}"

# 2. Restore Redis
echo -e "${YELLOW}📦 [2/4] Restoring Redis...${NC}"
if [ -f "$SCRIPT_DIR/redis_dump.rdb" ]; then
    docker stop bizskill-redis
    docker cp "$SCRIPT_DIR/redis_dump.rdb" bizskill-redis:/data/dump.rdb
    docker start bizskill-redis
    sleep 3
    echo -e "${GREEN}✅ Redis restored${NC}"
else
    echo -e "${YELLOW}⚠️  No Redis backup found, skipping${NC}"
fi

# 3. Restore Qdrant
echo -e "${YELLOW}📦 [3/4] Restoring Qdrant vector database...${NC}"
if [ -f "$SCRIPT_DIR/qdrant_data.tar.gz" ]; then
    docker stop bizskill-qdrant
    docker run --rm \
        -v bizskill_qdrant_data:/target \
        -v "$SCRIPT_DIR":/backup:ro \
        alpine sh -c "rm -rf /target/* && tar xzf /backup/qdrant_data.tar.gz -C /target"
    docker start bizskill-qdrant
    sleep 5
    echo -e "${GREEN}✅ Qdrant restored${NC}"
else
    echo -e "${YELLOW}⚠️  No Qdrant backup found, skipping${NC}"
fi

# 4. Restore HuggingFace cache
echo -e "${YELLOW}📦 [4/4] Restoring ML model cache...${NC}"
if [ -f "$SCRIPT_DIR/huggingface_cache.tar.gz" ]; then
    docker run --rm \
        -v bizskill_huggingface_cache:/target \
        -v "$SCRIPT_DIR":/backup:ro \
        alpine sh -c "rm -rf /target/* && tar xzf /backup/huggingface_cache.tar.gz -C /target"
    echo -e "${GREEN}✅ ML model cache restored${NC}"
else
    echo -e "${YELLOW}⚠️  No ML cache backup, models will be re-downloaded on first use${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration completed successfully!"
echo -e "==========================================${NC}"
echo ""
echo "Restart your services with:"
echo "  docker-compose -f docker-compose.prod.yml restart"
RESTORE_SCRIPT

chmod +x "$MIGRATION_DIR/restore.sh"

# Create final archive
echo ""
echo -e "${YELLOW}📦 Creating migration archive...${NC}"
ARCHIVE_NAME="bizskill_migration_$(date +%Y%m%d_%H%M%S).tar.gz"
tar czf "$ARCHIVE_NAME" -C "$(dirname $MIGRATION_DIR)" "$(basename $MIGRATION_DIR)"

# Get archive size
ARCHIVE_SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Migration package created!"
echo -e "==========================================${NC}"
echo ""
echo -e "📁 Archive: ${BLUE}$ARCHIVE_NAME${NC} ($ARCHIVE_SIZE)"
echo ""
echo -e "${YELLOW}📤 To transfer to your server:${NC}"
echo ""
echo "  # Option 1: Using scp"
echo "  scp $ARCHIVE_NAME user@your-server-ip:/path/to/BizSkill/"
echo ""
echo "  # Option 2: Using rsync (resumable)"
echo "  rsync -avz --progress $ARCHIVE_NAME user@your-server-ip:/path/to/BizSkill/"
echo ""
echo -e "${YELLOW}📥 On your production server:${NC}"
echo ""
echo "  cd /path/to/BizSkill"
echo "  tar xzf $ARCHIVE_NAME"
echo "  cd $(basename $MIGRATION_DIR)"
echo "  ./restore.sh"
echo ""

# Cleanup temp directory
rm -rf "$MIGRATION_DIR"
