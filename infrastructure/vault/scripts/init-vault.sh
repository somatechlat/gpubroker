#!/bin/bash
# ============================================
# Vault Initialization Script
# GPUBROKER - Enterprise Secret Management
# ============================================
# This script initializes Vault and sets up the secrets engine
# Run this ONCE after first Vault deployment

set -e

VAULT_ADDR=${VAULT_ADDR:-"http://127.0.0.1:8200"}
export VAULT_ADDR

echo "============================================"
echo "GPUBROKER Vault Initialization"
echo "============================================"

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
until curl -s ${VAULT_ADDR}/v1/sys/health > /dev/null 2>&1; do
    sleep 2
done
echo "Vault is ready!"

# Check if already initialized
INIT_STATUS=$(curl -s ${VAULT_ADDR}/v1/sys/init | jq -r '.initialized')

if [ "$INIT_STATUS" = "true" ]; then
    echo "Vault is already initialized."
    echo "If you need to re-initialize, delete /vault/data and restart."
    exit 0
fi

echo "Initializing Vault..."

# Initialize Vault with 5 key shares and 3 key threshold
INIT_RESPONSE=$(curl -s -X PUT ${VAULT_ADDR}/v1/sys/init \
    -H "Content-Type: application/json" \
    -d '{"secret_shares": 5, "secret_threshold": 3}')

# Extract keys and root token
echo "$INIT_RESPONSE" | jq -r '.keys[]' > /vault/config/unseal-keys.txt
ROOT_TOKEN=$(echo "$INIT_RESPONSE" | jq -r '.root_token')
echo "$ROOT_TOKEN" > /vault/config/root-token.txt

echo "============================================"
echo "⚠️  CRITICAL: SAVE THESE SECURELY!"
echo "============================================"
echo "Unseal Keys saved to: /vault/config/unseal-keys.txt"
echo "Root Token saved to: /vault/config/root-token.txt"
echo ""
echo "In production, distribute unseal keys to different people"
echo "and store root token in a secure location!"
echo "============================================"

# Unseal Vault (using first 3 keys)
echo "Unsealing Vault..."
KEY1=$(sed -n '1p' /vault/config/unseal-keys.txt)
KEY2=$(sed -n '2p' /vault/config/unseal-keys.txt)
KEY3=$(sed -n '3p' /vault/config/unseal-keys.txt)

curl -s -X PUT ${VAULT_ADDR}/v1/sys/unseal -d "{\"key\": \"$KEY1\"}" > /dev/null
curl -s -X PUT ${VAULT_ADDR}/v1/sys/unseal -d "{\"key\": \"$KEY2\"}" > /dev/null
curl -s -X PUT ${VAULT_ADDR}/v1/sys/unseal -d "{\"key\": \"$KEY3\"}" > /dev/null

echo "Vault unsealed!"

# Enable KV secrets engine v2
echo "Enabling KV secrets engine..."
curl -s -X POST ${VAULT_ADDR}/v1/sys/mounts/secret \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"type": "kv", "options": {"version": "2"}}'

echo "KV secrets engine enabled at 'secret/'"

# Create policies
echo "Creating policies..."

# Read-only policy for services
curl -s -X PUT ${VAULT_ADDR}/v1/sys/policies/acl/gpubroker-service \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"secret/data/gpubroker/*\" { capabilities = [\"read\", \"list\"] }"
    }'

# Admin policy
curl -s -X PUT ${VAULT_ADDR}/v1/sys/policies/acl/gpubroker-admin \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "policy": "path \"secret/*\" { capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\"] }"
    }'

echo "Policies created!"

# Enable AppRole auth method for services
echo "Enabling AppRole auth..."
curl -s -X POST ${VAULT_ADDR}/v1/sys/auth/approle \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"type": "approle"}'

# Create AppRole for services
curl -s -X POST ${VAULT_ADDR}/v1/auth/approle/role/gpubroker-service \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "token_policies": ["gpubroker-service"],
        "token_ttl": "1h",
        "token_max_ttl": "4h",
        "secret_id_ttl": "720h"
    }'

echo "AppRole created!"

# Get Role ID and Secret ID for services
ROLE_ID=$(curl -s ${VAULT_ADDR}/v1/auth/approle/role/gpubroker-service/role-id \
    -H "X-Vault-Token: $ROOT_TOKEN" | jq -r '.data.role_id')

SECRET_ID=$(curl -s -X POST ${VAULT_ADDR}/v1/auth/approle/role/gpubroker-service/secret-id \
    -H "X-Vault-Token: $ROOT_TOKEN" | jq -r '.data.secret_id')

echo "$ROLE_ID" > /vault/config/approle-role-id.txt
echo "$SECRET_ID" > /vault/config/approle-secret-id.txt

echo "============================================"
echo "AppRole Credentials (for services):"
echo "Role ID: $ROLE_ID"
echo "Secret ID: $SECRET_ID"
echo "============================================"

echo ""
echo "✅ Vault initialization complete!"
echo ""
echo "Next steps:"
echo "1. Store provider API keys: ./store-secrets.sh"
echo "2. Configure services to use Vault"
echo "============================================"
