# GPUBROKER Database-Backed Configuration System

## Overview

GPUBROKER uses **Django ORM-based configuration management** following Django standards. ALL secrets and configuration are stored in the PostgreSQL database, encrypted at rest.

## Architecture

```
Vault (Initial Secrets) → Django Database (Encrypted) → Application Runtime
```

1. **Vault**: Stores secrets during initialization only
2. **Django Database**: Central source of truth for ALL configuration (encrypted)
3. **Application**: Reads configuration from database at runtime

## Key Principles

✅ **NO passwords in environment variables**
✅ **NO secrets in .env files**
✅ **ALL configuration in Django database**
✅ **Django ORM standards followed**
✅ **Encrypted at rest using django-encrypted-model-fields**

## Configuration Models

### 1. Configuration (General)
- Key-value configuration storage
- Supports encrypted values for secrets
- Categories: database, cache, security, api, feature, service, monitoring

### 2. DatabaseConfiguration
- Database connection settings
- Encrypted passwords
- Connection pooling options

### 3. CacheConfiguration
- Redis/cache configuration
- Encrypted passwords
- Connection pool settings

### 4. ServiceConfiguration
- External service credentials (Stripe, AWS, SendGrid, etc.)
- Encrypted API keys and secrets

## Startup Sequence

### Development Environment

```bash
cd infrastructure/docker
./start-dev.sh
```

**What happens:**
1. Starts Vault, PostgreSQL, Redis, Kafka, Zookeeper, ClickHouse
2. Initializes Vault with generated secrets
3. Starts Django container
4. Django runs migrations (creates configuration tables)
5. Django loads secrets from Vault → Database (one-time)
6. Django starts using database-backed configuration
7. Starts frontend, nginx, monitoring services

### Manual Steps

```bash
# 1. Start infrastructure
docker compose -f docker-compose.dev.yml up -d vault postgres redis

# 2. Initialize Vault
./init-vault-secrets.sh

# 3. Start Django
docker compose -f docker-compose.dev.yml up -d django

# 4. Check Django logs
docker compose -f docker-compose.dev.yml logs -f django
```

## Environment Variables

### Bootstrap Variables (Required)
These are ONLY for initial database connection:

```bash
BOOTSTRAP_DB_NAME=gpubroker
BOOTSTRAP_DB_USER=gpubroker
BOOTSTRAP_DB_PASSWORD=gpubroker_bootstrap_temp
BOOTSTRAP_DB_HOST=postgres
BOOTSTRAP_DB_PORT=5432
```

### Vault Variables (Required for initialization)
```bash
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root
```

### Runtime Variables (Non-sensitive)
```bash
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

## Configuration Management

### View Configuration

```python
from shared.models.configuration import Configuration

# Get value
secret_key = Configuration.objects.get_value('django.secret_key', decrypt=True)

# Set value
Configuration.objects.set_value(
    key='feature.new_ui',
    value=True,
    is_secret=False,
    description='Enable new UI'
)
```

### Database Configuration

```python
from shared.models.configuration import DatabaseConfiguration

# Get Django config
db_config = DatabaseConfiguration.objects.get(name='default')
django_config = db_config.get_django_config()
```

### Cache Configuration

```python
from shared.models.configuration import CacheConfiguration

# Get Django config
cache_config = CacheConfiguration.objects.get(name='default')
django_config = cache_config.get_django_config()
```

## Security

### Encryption
- Uses `django-encrypted-model-fields`
- AES-256 encryption
- Encryption key derived from Django SECRET_KEY
- All passwords, API keys, tokens encrypted at rest

### Access Control
- Configuration only accessible via Django ORM
- No direct database access needed
- Audit trail via created_at/updated_at timestamps

## Troubleshooting

### Django won't start

```bash
# Check PostgreSQL
docker compose -f docker-compose.dev.yml logs postgres

# Check Vault
docker compose -f docker-compose.dev.yml logs vault

# Check Django
docker compose -f docker-compose.dev.yml logs django
```

### Configuration not loading

```bash
# Enter Django container
docker compose -f docker-compose.dev.yml exec django bash

# Check configuration
python manage.py shell
>>> from shared.models.configuration import Configuration
>>> Configuration.objects.all()
```

### Re-initialize configuration

```bash
# Enter Django container
docker compose -f docker-compose.dev.yml exec django bash

# Re-run initialization
python manage.py init_config_from_vault
```

## Migration from Environment Variables

If you have existing environment-based configuration:

1. Create Configuration entries in database
2. Update code to use `Configuration.objects.get_value()`
3. Remove environment variables
4. Test thoroughly

## Best Practices

1. **Never hardcode secrets** - Always use Configuration model
2. **Use categories** - Organize configuration by category
3. **Add descriptions** - Document what each config does
4. **Use is_secret flag** - Mark sensitive data appropriately
5. **Cache wisely** - Configuration is cached for 5 minutes
6. **Audit changes** - Track who changed what and when

## Port Ranges

All GPUBROKER services use ports in the **28000-28999** range:

- 28001: PostgreSQL
- 28002: ClickHouse HTTP
- 28003: ClickHouse Native
- 28004: Redis
- 28005: Vault
- 28007: Kafka (KRaft mode - no Zookeeper)
- 28010: Nginx (main entry point)
- 28030: Frontend
- 28031: Prometheus
- 28032: Grafana
- 28080: Django (internal)

## Container Naming

All containers use the `gpubroker_` prefix:

- gpubroker_postgres
- gpubroker_redis
- gpubroker_vault
- gpubroker_django
- gpubroker_frontend
- gpubroker_nginx
- etc.
