#!/bin/bash
# ============================================
# GPUBROKER - Local Production Start Script
# ============================================
# Starts the full Docker cluster with production-like settings
# Memory Limit: 10GB total, Persistent Volumes
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  GPUBROKER - Local Production Cluster${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed.${NC}"
    exit 1
fi

# Set defaults for required environment variables if not in .env
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-gpubroker_secure_local}"
export CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-clickhouse_secure_local}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-django-local-prod-key-$(date +%s)}"
export GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin_local_secure}"

# Display memory allocation
echo -e "${YELLOW}Memory Allocation (10GB Total):${NC}"
echo "  • PostgreSQL:  1.0 GB"
echo "  • Redis:       384 MB"
echo "  • Kafka:       1.0 GB"
echo "  • Zookeeper:   512 MB"
echo "  • ClickHouse:  1.5 GB"
echo "  • Django:      1.5 GB"
echo "  • Frontend:    1.0 GB"
echo "  • Prometheus:  512 MB"
echo "  • Grafana:     384 MB"
echo "  • Vault:       384 MB"
echo "  • Nginx:       128 MB"
echo "  ─────────────────────"
echo "  Total:         ~8.3 GB (headroom for spikes)"
echo ""

# Parse command line arguments
ACTION="${1:-up}"
SERVICES="${@:2}"

case "$ACTION" in
    up|start)
        echo -e "${GREEN}Starting GPUBROKER cluster...${NC}"
        echo ""
        
        # Pull latest images
        echo -e "${BLUE}Pulling images...${NC}"
        docker compose -f docker-compose.local-prod.yml pull --quiet 2>/dev/null || true
        
        # Start services
        echo -e "${BLUE}Starting services...${NC}"
        if [ -n "$SERVICES" ]; then
            docker compose -f docker-compose.local-prod.yml up -d $SERVICES
        else
            docker compose -f docker-compose.local-prod.yml up -d
        fi
        
        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}  Cluster Started Successfully!${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo ""
        echo -e "${YELLOW}Service URLs:${NC}"
        echo "  • Landing Page:     http://localhost:80"
        echo "  • Django API:       http://localhost:28080"
        echo "  • API Docs:         http://localhost:28080/api/v2/docs"
        echo "  • Frontend:         http://localhost:28030"
        echo "  • Grafana:          http://localhost:28032 (admin/${GRAFANA_PASSWORD:-admin_local_secure})"
        echo "  • Prometheus:       http://localhost:28031"
        echo ""
        echo -e "${YELLOW}Database Access:${NC}"
        echo "  • PostgreSQL:       localhost:28001 (gpubroker/${POSTGRES_PASSWORD})"
        echo "  • Redis:            localhost:28004"
        echo "  • ClickHouse:       localhost:28002"
        echo "  • Kafka:            localhost:28007"
        echo ""
        echo -e "${BLUE}Waiting for services to be healthy...${NC}"
        sleep 5
        docker compose -f docker-compose.local-prod.yml ps
        ;;
        
    down|stop)
        echo -e "${YELLOW}Stopping GPUBROKER cluster...${NC}"
        docker compose -f docker-compose.local-prod.yml down
        echo -e "${GREEN}Cluster stopped.${NC}"
        ;;
        
    restart)
        echo -e "${YELLOW}Restarting GPUBROKER cluster...${NC}"
        docker compose -f docker-compose.local-prod.yml restart $SERVICES
        echo -e "${GREEN}Cluster restarted.${NC}"
        ;;
        
    logs)
        if [ -n "$SERVICES" ]; then
            docker compose -f docker-compose.local-prod.yml logs -f $SERVICES
        else
            docker compose -f docker-compose.local-prod.yml logs -f
        fi
        ;;
        
    status|ps)
        echo -e "${BLUE}GPUBROKER Cluster Status:${NC}"
        echo ""
        docker compose -f docker-compose.local-prod.yml ps
        echo ""
        echo -e "${BLUE}Resource Usage:${NC}"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | grep gpubroker || echo "No containers running"
        ;;
        
    clean)
        echo -e "${RED}WARNING: This will remove all containers and volumes!${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose -f docker-compose.local-prod.yml down -v --remove-orphans
            echo -e "${GREEN}Cleaned up all containers and volumes.${NC}"
        fi
        ;;
        
    migrate)
        echo -e "${BLUE}Running Django migrations...${NC}"
        docker compose -f docker-compose.local-prod.yml exec django python manage.py migrate
        ;;
        
    shell)
        echo -e "${BLUE}Opening Django shell...${NC}"
        docker compose -f docker-compose.local-prod.yml exec django python manage.py shell
        ;;
        
    build)
        echo -e "${BLUE}Building images...${NC}"
        docker compose -f docker-compose.local-prod.yml build $SERVICES
        ;;
        
    *)
        echo "Usage: $0 {up|down|restart|logs|status|clean|migrate|shell|build} [services...]"
        echo ""
        echo "Commands:"
        echo "  up, start     Start the cluster (default)"
        echo "  down, stop    Stop the cluster"
        echo "  restart       Restart the cluster or specific services"
        echo "  logs          View logs (add service name for specific logs)"
        echo "  status, ps    Show cluster status and resource usage"
        echo "  clean         Remove all containers and volumes (destructive!)"
        echo "  migrate       Run Django migrations"
        echo "  shell         Open Django shell"
        echo "  build         Build images"
        exit 1
        ;;
esac
