#!/bin/bash

# ⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
# We do NOT mock, bypass, or invent data.
# We use ONLY real servers, real APIs, and real data.
# This codebase follows principles of truth, simplicity, and elegance.

set -e  # Exit on any error

echo "🚀 GPUBROKER Rapid Development Startup Script"
echo "============================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file from template."
    echo "⚠️  IMPORTANT: Edit .env file with your REAL API keys before continuing!"
    echo ""
    echo "You need to add real API keys for:"
    echo "  - RUNPOD_API_KEY"
    echo "  - VASTAI_API_KEY" 
    echo "  - COREWEAVE_API_KEY"
    echo "  - HUGGINGFACE_API_KEY"
    echo "  - And other provider keys as needed"
    echo ""
    read -p "Press Enter after you've added your real API keys to .env file..."
fi

echo "🔧 Setting up development environment..."

# Create necessary directories
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/clickhouse
mkdir -p data/redis
mkdir -p data/minio

echo "📦 Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "✅ Frontend dependencies already installed"
fi
cd ..

echo "🐳 Building and starting services with Docker Compose..."

# Build and start all services
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for PostgreSQL to be ready
echo "🐘 Waiting for PostgreSQL..."
until docker-compose exec postgres pg_isready -U gpubroker > /dev/null 2>&1; do
    printf "."
    sleep 2
done
echo " ✅ PostgreSQL ready"

# Wait for Redis to be ready  
echo "🔴 Waiting for Redis..."
until docker-compose exec redis redis-cli --raw incr ping > /dev/null 2>&1; do
    printf "."
    sleep 2
done
echo " ✅ Redis ready"

# Wait for ClickHouse to be ready
echo "🏠 Waiting for ClickHouse..."
until curl -s http://localhost:8123/ping > /dev/null 2>&1; do
    printf "."
    sleep 2
done
echo " ✅ ClickHouse ready"

echo ""
echo "🎉 GPUBROKER is now running!"
echo ""
echo "📍 Service URLs:"
echo "  🌐 Frontend Dashboard:    http://localhost:3000"
echo "  🔐 Auth Service:         http://localhost:8001"
echo "  🔌 Provider Service:     http://localhost:8002"  
echo "  📊 KPI Service:          http://localhost:8003"
echo "  📈 Prometheus:           http://localhost:9090"
echo "  📊 Grafana:              http://localhost:3001 (admin/grafana_dev_password_2024)"
echo "  🐘 PostgreSQL:           localhost:5432 (gpubroker/gpubroker_dev_password_2024)"
echo "  🔴 Redis:                localhost:6379 (redis_dev_password_2024)"
echo "  🏠 ClickHouse:           http://localhost:8123"
echo ""
echo "📖 API Documentation:"
echo "  🔐 Auth Service API:     http://localhost:8001/docs"
echo "  🔌 Provider Service API: http://localhost:8002/docs"
echo "  📊 KPI Service API:      http://localhost:8003/docs"
echo ""
echo "🔍 Health Checks:"
docker-compose ps

echo ""
echo "🚀 Quick Test Commands:"
echo "  # Check auth service health"
echo "  curl http://localhost:8001/health"
echo ""
echo "  # Check provider service health" 
echo "  curl http://localhost:8002/health"
echo ""
echo "  # Check KPI service health"
echo "  curl http://localhost:8003/health"
echo ""
echo "  # List available providers"
echo "  curl http://localhost:8002/providers"
echo ""

echo "📝 Next Steps:"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Check service logs: docker-compose logs -f [service-name]"
echo "  3. Add more real provider API keys to .env as needed"
echo "  4. Start developing new features!"
echo ""

echo "🛑 To stop all services:"
echo "  docker-compose down"
echo ""

echo "✨ Happy coding with REAL data and REAL APIs! ✨"