#!/bin/bash
# ============================================
# GPUBROKER - Quick Database Reset (Data Only)
# ============================================
# Resets all database tables WITHOUT removing volumes
# Faster than full clean slate - for development
#
# Usage: ./scripts/reset-db.sh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "🔄 GPUBROKER QUICK DATABASE RESET"  
echo "============================================"
echo ""

# Check if Django container is running
if ! docker-compose -f docker-compose.local-prod.yml ps django | grep -q "Up"; then
    echo "⚠️  Django container not running. Starting..."
    docker-compose -f docker-compose.local-prod.yml up -d postgres redis django
    sleep 10
fi

echo "📍 Step 1: Clearing all subscriptions..."
docker-compose -f docker-compose.local-prod.yml exec -T postgres \
    psql -U gpubroker -d gpubroker -c "TRUNCATE TABLE gpubroker_subscriptions, gpubroker_payments, gpubroker_pod_metrics RESTART IDENTITY CASCADE;" 2>/dev/null || \
    echo "   Tables may not exist yet, will be created by migrations"

echo ""
echo "📍 Step 2: Clearing Redis cache..."
docker-compose -f docker-compose.local-prod.yml exec -T redis redis-cli FLUSHALL

echo ""
echo "📍 Step 3: Running fresh migrations..."
docker-compose -f docker-compose.local-prod.yml exec -T django python manage.py migrate --noinput

echo ""
echo "============================================"
echo "✅ DATABASE RESET COMPLETE!"
echo "============================================"
echo ""
echo "📊 Tables cleared:"
echo "   - gpubroker_subscriptions"
echo "   - gpubroker_payments"  
echo "   - gpubroker_pod_metrics"
echo "   - Redis cache"
echo ""
echo "🧪 Ready for fresh testing!"
echo ""
