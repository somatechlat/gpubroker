#!/bin/bash

# ⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
# We do NOT mock, bypass, or invent data.
# We use ONLY real servers, real APIs, and real data.
# This codebase follows principles of truth, simplicity, and elegance.

set -e  # Exit on any error

# Load env if present to pick up port overrides
if [ -f ".env" ]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.dev.yml}

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
    echo "🔐 Secrets belong in HashiCorp Vault, not .env."
    echo "   Load provider/cloud API keys via infrastructure/vault/scripts/store-secrets.sh"
    echo ""
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
docker-compose -f "$COMPOSE_FILE" up --build -d

echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for PostgreSQL to be ready
echo "🐘 Waiting for PostgreSQL..."
until docker-compose -f "$COMPOSE_FILE" exec postgres pg_isready -U gpubroker > /dev/null 2>&1; do
    printf "."
    sleep 2
done
echo " ✅ PostgreSQL ready"

# Wait for Redis to be ready  
echo "🔴 Waiting for Redis..."
until docker-compose -f "$COMPOSE_FILE" exec redis redis-cli --raw incr ping > /dev/null 2>&1; do
    printf "."
    sleep 2
done
echo " ✅ Redis ready"

# Wait for ClickHouse to be ready
CLICKHOUSE_HTTP_PORT=${PORT_CLICKHOUSE_HTTP:-28002}
echo "🏠 Waiting for ClickHouse on ${CLICKHOUSE_HTTP_PORT}..."
until curl -s "http://localhost:${CLICKHOUSE_HTTP_PORT}/ping" > /dev/null 2>&1; do
    printf "."
    sleep 2
done
echo " ✅ ClickHouse ready"

echo ""
echo "🎉 GPUBROKER is now running!"
echo ""
echo "📍 Service URLs:"
echo "  🌐 Frontend Dashboard:    http://localhost:${PORT_FRONTEND:-28030}"
echo "  🔐 Auth Service:         http://localhost:${PORT_AUTH:-28020}"
echo "  🔌 Provider Service:     http://localhost:${PORT_PROVIDER:-28021}"  
echo "  📊 KPI Service:          http://localhost:${PORT_KPI:-28022}"
echo "  🧠 Math Core:            http://localhost:${PORT_MATH:-28023}"
echo "  🔔 WebSocket Gateway:    ws://localhost:${PORT_WS_GATEWAY:-28025}/ws"
echo "  📈 Prometheus:           http://localhost:${PORT_PROMETHEUS:-28031}"
echo "  📊 Grafana:              http://localhost:${PORT_GRAFANA:-28032}"
echo "  🐘 PostgreSQL:           localhost:${PORT_POSTGRES:-28001} (credentials from env/Vault)"
echo "  🔴 Redis:                localhost:${PORT_REDIS:-28004}"
echo "  🏠 ClickHouse:           http://localhost:${PORT_CLICKHOUSE_HTTP:-28002}"
echo ""
echo "📖 API Documentation:"
echo "  🔐 Auth Service API:     http://localhost:${PORT_AUTH:-28020}/docs"
echo "  🔌 Provider Service API: http://localhost:${PORT_PROVIDER:-28021}/docs"
echo "  📊 KPI Service API:      http://localhost:${PORT_KPI:-28022}/docs"
echo ""
echo "🔍 Health Checks:"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "🚀 Quick Test Commands:"
echo "  # Check auth service health"
echo "  curl http://localhost:${PORT_AUTH:-28020}/health"
echo ""
echo "  # Check provider service health" 
echo "  curl http://localhost:${PORT_PROVIDER:-28021}/health"
echo ""
echo "  # Check KPI service health"
echo "  curl http://localhost:${PORT_KPI:-28022}/health"
echo ""
echo "  # List available providers"
echo "  curl http://localhost:${PORT_PROVIDER:-28021}/providers"
echo ""

echo "📝 Next Steps:"
echo "  1. Open http://localhost:${PORT_FRONTEND:-28030} in your browser"
echo "  2. Check service logs: docker-compose -f $COMPOSE_FILE logs -f [service-name]"
echo "  3. Store provider API keys in Vault using infrastructure/vault/scripts/store-secrets.sh"
echo "  4. Start developing new features!"
echo ""

echo "🛑 To stop all services:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""

echo "✨ Happy coding with REAL data and REAL APIs! ✨"
