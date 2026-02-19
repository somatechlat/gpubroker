#!/bin/bash
# Initialize Vault with GPUBROKER secrets
# This script runs ONCE to populate Vault with all required secrets

set -e

VAULT_ADDR=${VAULT_ADDR:-http://localhost:28005}
VAULT_TOKEN=${VAULT_TOKEN:-root}

echo "🔐 Initializing Vault secrets for GPUBROKER..."

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
max_attempts=30
attempt=0
while ! curl -s -f "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ Vault not ready after $max_attempts attempts"
        exit 1
    fi
    echo "Vault not ready, waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done
echo "✅ Vault is ready!"

# Enable KV v2 secrets engine
echo "Enabling KV v2 secrets engine..."
curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -d '{"type":"kv-v2"}' \
    "${VAULT_ADDR}/v1/sys/mounts/secret" || echo "KV engine already enabled"

# Generate secure random passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
CLICKHOUSE_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# Generate JWT keys
echo "Generating JWT RSA key pair..."
openssl genrsa -out /tmp/jwt_private.pem 2048 2>/dev/null
openssl rsa -in /tmp/jwt_private.pem -pubout -out /tmp/jwt_public.pem 2>/dev/null

# Read keys and escape for JSON using Python
JWT_PRIVATE_KEY=$(python3 -c "import json; print(json.dumps(open('/tmp/jwt_private.pem').read()))" | sed 's/^"//;s/"$//')
JWT_PUBLIC_KEY=$(python3 -c "import json; print(json.dumps(open('/tmp/jwt_public.pem').read()))" | sed 's/^"//;s/"$//')

# Clean up temp files
rm -f /tmp/jwt_private.pem /tmp/jwt_public.pem

echo "📝 Storing secrets in Vault..."

# Store database secrets
curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -d "{\"data\":{\"password\":\"${POSTGRES_PASSWORD}\",\"username\":\"gpubroker\",\"database\":\"gpubroker\",\"host\":\"postgres\",\"port\":\"5432\"}}" \
    "${VAULT_ADDR}/v1/secret/data/database/postgres"

# Store Redis secrets
curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -d "{\"data\":{\"password\":\"${REDIS_PASSWORD}\",\"host\":\"redis\",\"port\":\"6379\"}}" \
    "${VAULT_ADDR}/v1/secret/data/database/redis"

# Store ClickHouse secrets
curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -d "{\"data\":{\"password\":\"${CLICKHOUSE_PASSWORD}\",\"username\":\"gpubroker\",\"database\":\"gpubroker\",\"host\":\"clickhouse\",\"port\":\"8123\"}}" \
    "${VAULT_ADDR}/v1/secret/data/database/clickhouse"

# Store Django secrets
curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -d "{\"data\":{\"secret_key\":\"${DJANGO_SECRET_KEY}\"}}" \
    "${VAULT_ADDR}/v1/secret/data/django/config"

# Store JWT keys
curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"data\":{\"private_key\":\"${JWT_PRIVATE_KEY}\",\"public_key\":\"${JWT_PUBLIC_KEY}\"}}" \
    "${VAULT_ADDR}/v1/secret/data/jwt/keys"

echo "✅ All secrets stored in Vault successfully!"
echo ""
echo "📋 Secret paths in Vault:"
echo "  - secret/data/database/postgres"
echo "  - secret/data/database/redis"
echo "  - secret/data/database/clickhouse"
echo "  - secret/data/django/config"
echo "  - secret/data/jwt/keys"
echo ""
echo "🔑 Vault Token: ${VAULT_TOKEN}"
echo "🌐 Vault Address: ${VAULT_ADDR}"
