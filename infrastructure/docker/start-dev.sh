#!/bin/bash
# GPUBROKER Development Environment Startup Script
# Starts all services with proper initialization sequence

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "🚀 GPUBROKER Development Environment"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with required configuration."
    exit 1
fi

# Load environment variables
source .env

echo "📋 Configuration:"
echo "  - Vault: http://localhost:${PORT_VAULT:-28005}"
echo "  - PostgreSQL: localhost:${PORT_POSTGRES:-28001}"
echo "  - Redis: localhost:${PORT_REDIS:-28004}"
echo "  - Django: localhost:${PORT_DJANGO:-28080}"
echo "  - Nginx: localhost:${PORT_NGINX:-28010}"
echo "  - Frontend: localhost:${PORT_FRONTEND:-28030}"
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose -f docker-compose.dev.yml down 2>/dev/null || true
echo ""

# Clean up old volumes (optional - comment out if you want to keep data)
# echo "🧹 Cleaning up old volumes..."
# docker volume prune -f
# echo ""

# Start infrastructure services first
echo "🏗️  Starting infrastructure services..."
docker compose -f docker-compose.dev.yml up -d vault postgres redis kafka clickhouse
echo ""

# Wait for Vault to be ready
echo "⏳ Waiting for Vault to be ready..."
max_attempts=30
attempt=0
while ! curl -s -f "http://localhost:${PORT_VAULT:-28005}/v1/sys/health" > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ Vault not ready after $max_attempts attempts"
        echo "Checking Vault status..."
        docker compose -f docker-compose.dev.yml logs vault --tail=20
        exit 1
    fi
    sleep 2
done
echo "✅ Vault is ready!"
echo ""

# Initialize Vault with secrets
echo "🔐 Initializing Vault with secrets..."
bash init-vault-secrets.sh
echo ""

# Start Django application
echo "🐍 Starting Django application..."
docker compose -f docker-compose.dev.yml up -d --build django
echo ""

# Wait for Django to be ready
echo "⏳ Waiting for Django to be ready..."
attempt=0
while ! docker compose -f docker-compose.dev.yml exec -T django python /app/health_check.py > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge 60 ]; then
        echo "❌ Django not ready after 60 attempts"
        echo "📋 Django logs:"
        docker compose -f docker-compose.dev.yml logs django --tail=50
        exit 1
    fi
    sleep 2
done
echo "✅ Django is ready!"
echo ""

# Start remaining services
echo "🌐 Starting frontend and proxy services..."
docker compose -f docker-compose.dev.yml up -d frontend nginx prometheus grafana
echo ""

# Show status
echo "================================================"
echo "✅ GPUBROKER Development Environment is ready!"
echo "================================================"
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.dev.yml ps
echo ""
echo "🌐 Access Points:"
echo "  - Main Application: http://localhost:${PORT_NGINX:-28010}"
echo "  - Django API: http://localhost:${PORT_DJANGO:-28080}/api/v2"
echo "  - Django Admin: http://localhost:${PORT_DJANGO:-28080}/admin"
echo "  - Frontend: http://localhost:${PORT_FRONTEND:-28030}"
echo "  - Vault UI: http://localhost:${PORT_VAULT:-28005}"
echo "  - Prometheus: http://localhost:${PORT_PROMETHEUS:-28031}"
echo "  - Grafana: http://localhost:${PORT_GRAFANA:-28032}"
echo ""
echo "👤 Default Credentials (Development):"
echo "  - Django Admin: admin / admin123"
echo "  - Vault Token: ${VAULT_TOKEN}"
echo ""
echo "📋 Useful Commands:"
echo "  - View logs: docker compose -f docker-compose.dev.yml logs -f [service]"
echo "  - Stop all: docker compose -f docker-compose.dev.yml down"
echo "  - Restart service: docker compose -f docker-compose.dev.yml restart [service]"
echo ""
echo "🎯 Ready to develop!"
