#!/bin/bash
# Initialize Django configuration from Vault
# This script runs ONCE on first startup to populate database with configuration

set -e

echo "🔐 Initializing Django configuration from Vault..."

# Wait for Vault to be ready
echo "Waiting for Vault..."
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

# Check if configuration is already initialized
echo "Checking if configuration is already initialized..."
if python manage.py shell -c "from shared.models.configuration import Configuration; print(Configuration.objects.filter(key='django.secret_key').exists())" 2>/dev/null | grep -q "True"; then
    echo "✅ Configuration already initialized, skipping..."
    exit 0
fi

# Initialize configuration from Vault
echo "📝 Loading configuration from Vault into database..."
python manage.py init_config_from_vault \
    --vault-addr="${VAULT_ADDR}" \
    --vault-token="${VAULT_TOKEN}"

echo "✅ Django configuration initialized successfully!"
