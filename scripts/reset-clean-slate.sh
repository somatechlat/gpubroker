#!/bin/bash
# ============================================
# GPUBROKER - Clean Slate Reset Script
# ============================================
# Wipes ALL data and starts fresh for testing
# 
# Usage: ./scripts/reset-clean-slate.sh
# 
# This will:
# 1. Stop all containers
# 2. Remove all data volumes (PostgreSQL, Redis, etc.)
# 3. Rebuild containers
# 4. Run migrations
# 5. Start fresh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "🚨 GPUBROKER CLEAN SLATE RESET"
echo "============================================"
echo ""
echo "⚠️  WARNING: This will DELETE all data including:"
echo "   - All subscriptions and registrations"
echo "   - All payment records"
echo "   - All POD records"
echo "   - Redis cache"
echo "   - ClickHouse analytics"
echo ""

# Check if --force flag is passed
if [ "$1" != "--force" ]; then
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
fi

echo ""
echo "📍 Step 1: Stopping all containers..."
docker-compose -f docker-compose.local-prod.yml down --remove-orphans || true

echo ""
echo "📍 Step 2: Removing data volumes..."

# Core data volumes to remove
DATA_VOLUMES=(
    "gpubroker_postgres_data"
    "gpubroker_redis_data"
    "gpubroker_clickhouse_data"
    "gpubroker_clickhouse_logs"
    "gpubroker_kafka_data"
    "gpubroker_zookeeper_data"
    "gpubroker_zookeeper_logs"
    "gpubroker_vault_data"
    "gpubroker_vault_logs"
)

for vol in "${DATA_VOLUMES[@]}"; do
    if docker volume ls | grep -q "$vol"; then
        echo "   Removing $vol..."
        docker volume rm "$vol" 2>/dev/null || true
    fi
done

echo ""
echo "📍 Step 3: Rebuilding Django container..."
docker-compose -f docker-compose.local-prod.yml build --no-cache django

echo ""
echo "📍 Step 4: Starting database services..."
docker-compose -f docker-compose.local-prod.yml up -d postgres redis

# Wait for PostgreSQL to be healthy
echo "   Waiting for PostgreSQL to be ready..."
sleep 10
until docker-compose -f docker-compose.local-prod.yml exec -T postgres pg_isready -U gpubroker; do
    sleep 2
done

echo ""
echo "📍 Step 5: Starting Django and running migrations..."
docker-compose -f docker-compose.local-prod.yml up -d django

# Wait for Django to start
echo "   Waiting for Django to start..."
sleep 10

# Run migrations inside container
echo "   Running migrations..."
docker-compose -f docker-compose.local-prod.yml exec -T django python manage.py migrate --noinput

echo ""
echo "📍 Step 6: Starting frontend..."
docker-compose -f docker-compose.local-prod.yml up -d frontend

echo ""
echo "============================================"
echo "✅ CLEAN SLATE RESET COMPLETE!"
echo "============================================"
echo ""
echo "🌐 Services:"
echo "   Landing Page: http://localhost:28080"
echo "   Dashboard:    http://localhost:28030"
echo "   PostgreSQL:   localhost:28001"
echo "   Redis:        localhost:28004"
echo ""
echo "📊 Database is EMPTY - ready for fresh testing!"
echo ""
echo "🧪 Test Data:"
echo "   Email: ai@somatech.dev"
echo "   RUC:   1790869571001"
echo "   Plan:  Pro ($40/mo)"
echo ""
echo "============================================"
