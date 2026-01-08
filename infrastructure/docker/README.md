# GPUBROKER Docker Compose Setup

This directory contains a complete Docker Compose setup for GPUBroker, providing an alternative to the Tilt/Kubernetes development environment.

## Overview

The docker-compose.yml file orchestrates the entire GPUBroker stack:
- **Core Infrastructure**: PostgreSQL, Redis
- **Messaging**: Kafka, Zookeeper
- **Analytics**: ClickHouse, Prometheus, Grafana
- **Backend**: Django API, WebSocket Gateway
- **Frontend**: Lit Web Components UI
- **Infrastructure**: Vault, SpiceDB
- **Orchestration**: Airflow, Flink
- **Proxy**: Nginx (unified access on port 10355)

## Memory Usage

Total memory footprint: ~8GB (within 10GB constraint)
- PostgreSQL: 512MB
- Redis: 128MB
- Kafka: 512MB
- ClickHouse: 512MB
- Django: 512MB
- Frontend: 256MB
- Monitoring: 512MB
- Airflow: 2GB (webserver + scheduler)
- Flink: 1GB
- Other services: ~1GB

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- Minimum 12GB RAM available
- Ports 10355, 28000-28050 available

### 2. Setup Environment
```bash
cd docker
cp .env.example .env
# Edit .env with your values
```

### 3. Generate Required Keys
```bash
# JWT Keys
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem

# Airflow Fernet Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copy to .env
echo "JWT_PRIVATE_KEY=$(cat jwt_private.pem | base64 -w 0)" >> .env
echo "JWT_PUBLIC_KEY=$(cat jwt_public.pem | base64 -w 0)" >> .env
echo "AIRFLOW__CORE__FERNET_KEY=<your-fernet-key>" >> .env
```

### 4. Start Services
```bash
# Start all services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 5. Access Services

| Service | URL | Description |
|---------|-----|-------------|
| Main Dashboard | http://localhost:10355 | Unified access point |
| API | http://localhost:10355/api/v2 | Django REST API |
| Frontend | http://localhost:10355 | Lit UI Dashboard |
| WebSocket | ws://localhost:10355/ws | Real-time updates |
| Airflow | http://localhost:10355/airflow | Workflow orchestration |
| Grafana | http://localhost:10355/grafana | Monitoring dashboard |
| Prometheus | http://localhost:10355/prometheus | Metrics collection |
| Direct Django | http://localhost:28050 | Django API (direct) |
| Direct Frontend | http://localhost:28052 | Frontend (direct) |

### 6. Initialize Database
```bash
# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Collect static files
docker-compose exec django python manage.py collectstatic --noinput
```

## Common Commands

### Management
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Restart specific service
docker-compose restart django

# Scale a service
docker-compose up -d --scale django=2

# Execute command in service
docker-compose exec django python manage.py shell

# View logs for specific service
docker-compose logs -f django
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U gpubroker -d gpubroker

# Backup database
docker-compose exec postgres pg_dump -U gpubroker gpubroker > backup.sql

# Restore database
docker-compose exec -T postgres psql -U gpubroker gpubroker < backup.sql
```

### Kafka Operations
```bash
# List topics
docker-compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list

# Create topic
docker-compose exec kafka kafka-topics --create --topic test --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1

# Consume messages
docker-compose exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic orders.created --from-beginning
```

## Development Workflow

### Live Reload (Frontend)
The frontend container mounts the source directory, so changes are reflected immediately:
```bash
# After making changes to frontend/src
docker-compose restart frontend
```

### Django Development
The backend container mounts the entire backend directory:
```bash
# After making changes to backend code
docker-compose restart django

# Or run development server with auto-reload
docker-compose exec django python manage.py runserver 0.0.0.0:8000
```

### Testing
```bash
# Run Django tests
docker-compose exec django pytest

# Run specific test
docker-compose exec django pytest tests/unit/test_matching_engine.py

# Run E2E tests (requires running services)
docker-compose exec django pytest tests/e2e/
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs <service-name>

# Check if port is already in use
lsof -i :10355

# Restart all services
docker-compose down && docker-compose up -d
```

### Database connection issues
```bash
# Check if PostgreSQL is running
docker-compose exec postgres pg_isready -U gpubroker -d gpubroker

# Check database logs
docker-compose logs postgres
```

### Kafka issues
```bash
# Check Kafka logs
docker-compose logs kafka

# Verify Kafka is accepting connections
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server kafka:9092
```

### Memory issues
```bash
# Check memory usage
docker stats

# Reduce memory limits in docker-compose.yml if needed
# Edit deploy.resources.limits.memory for each service
```

## Production Considerations

⚠️ **WARNING**: This docker-compose setup is for **development and testing only**.

For production, use the Kubernetes setup with Tilt:
```bash
cd /Users/macbookpro201916i964gb1tb/Documents/GitHub/gpubroker
tilt up
```

### Production Differences
1. **Security**: Use proper secrets management (Vault, AWS Secrets Manager)
2. **Scaling**: Use Kubernetes for auto-scaling
3. **Persistence**: Use production-grade storage (EBS, RDS, etc.)
4. **Monitoring**: Use managed services (CloudWatch, Datadog)
5. **Networking**: Use proper ingress controllers and TLS termination
6. **Backup**: Implement automated backup strategies

## Environment Variables Reference

See `.env.example` for all available variables. Key ones:

- `POSTGRES_PASSWORD`: PostgreSQL password
- `CLICKHOUSE_PASSWORD`: ClickHouse password
- `DJANGO_SECRET_KEY`: Django secret key
- `JWT_PRIVATE_KEY`: JWT signing key (base64 encoded)
- `JWT_PUBLIC_KEY`: JWT verification key (base64 encoded)
- `VAULT_TOKEN`: Vault dev token
- `SPICEDB_KEY`: SpiceDB shared secret
- `AIRFLOW__CORE__FERNET_KEY`: Airflow encryption key
- `AIRFLOW_ADMIN_PASSWORD`: Airflow UI password
- `GRAFANA_PASSWORD`: Grafana admin password

## Architecture Notes

### Network Isolation
All services run in the `gpubroker-net` bridge network with subnet `172.20.0.0/16`.

### Port Mapping
- `10355`: Main ingress (Nginx)
- `28000-28052`: Direct service access
- `5432`: PostgreSQL (internal only)
- `6379`: Redis (internal only)
- `9092`: Kafka (internal only)

### Volume Persistence
Data is persisted in Docker volumes:
- `postgres_data`: Database records
- `redis_data`: Cache and sessions
- `kafka_data`: Event logs
- `clickhouse_data`: Analytics data
- `grafana_data`: Dashboards and configs
- `django_media`: User uploads
- `django_static`: Static files
- `airflow_logs`: Workflow execution logs

## Support

For issues or questions:
1. Check the logs: `docker-compose logs <service>`
2. Verify environment variables: `docker-compose exec django env`
3. Review the main documentation in `/Users/macbookpro201916i964gb1tb/Documents/GitHub/gpubroker/docs/`
4. Check the SRS: `/Users/macbookpro201916i964gb1tb/Documents/GitHub/gpubroker/docs/srs/GPUBroker_SRS.md`

## License

GPUBroker - See main project LICENSE file
