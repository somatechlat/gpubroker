#!/bin/bash
# ============================================
# Store Provider API Keys in Vault
# GPUBROKER - Enterprise Secret Management
# ============================================
# Run this script to store your API keys in Vault
# Keys are read from environment variables or prompted

set -e

VAULT_ADDR=${VAULT_ADDR:-"http://127.0.0.1:8200"}
export VAULT_ADDR

# Get root token
if [ -f /vault/config/root-token.txt ]; then
    VAULT_TOKEN=$(cat /vault/config/root-token.txt)
elif [ -n "$VAULT_TOKEN" ]; then
    echo "Using VAULT_TOKEN from environment"
else
    echo "Error: No Vault token found. Run init-vault.sh first or set VAULT_TOKEN"
    exit 1
fi
export VAULT_TOKEN

echo "============================================"
echo "GPUBROKER - Store Provider API Keys"
echo "============================================"
echo ""
echo "Enter API keys for each provider."
echo "Press Enter to skip a provider."
echo "============================================"

# Function to store a secret
store_secret() {
    local path=$1
    local key=$2
    local value=$3
    
    if [ -n "$value" ]; then
        curl -s -X POST ${VAULT_ADDR}/v1/secret/data/gpubroker/${path} \
            -H "X-Vault-Token: $VAULT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"data\": {\"${key}\": \"${value}\"}}" > /dev/null
        echo "  ✅ Stored ${path}/${key}"
    else
        echo "  ⏭️  Skipped ${path}/${key}"
    fi
}

# Function to prompt for key
prompt_key() {
    local provider=$1
    local env_var=$2
    local current_value=${!env_var}
    
    if [ -n "$current_value" ]; then
        echo "  Using $env_var from environment"
        echo "$current_value"
    else
        read -sp "  Enter $provider API Key (or press Enter to skip): " value
        echo ""
        echo "$value"
    fi
}

echo ""
echo "--- HYPERSCALERS ---"

# AWS
echo "AWS SageMaker:"
AWS_KEY=$(prompt_key "AWS" "AWS_ACCESS_KEY_ID")
store_secret "aws" "access_key_id" "$AWS_KEY"
AWS_SECRET=$(prompt_key "AWS" "AWS_SECRET_ACCESS_KEY")
store_secret "aws" "secret_access_key" "$AWS_SECRET"

# Google
echo "Google Vertex AI:"
GOOGLE_KEY=$(prompt_key "Google" "GOOGLE_API_KEY")
store_secret "google" "api_key" "$GOOGLE_KEY"

# Azure
echo "Azure ML:"
AZURE_CLIENT=$(prompt_key "Azure" "AZURE_CLIENT_ID")
store_secret "azure" "client_id" "$AZURE_CLIENT"
AZURE_SECRET=$(prompt_key "Azure" "AZURE_CLIENT_SECRET")
store_secret "azure" "client_secret" "$AZURE_SECRET"
AZURE_TENANT=$(prompt_key "Azure" "AZURE_TENANT_ID")
store_secret "azure" "tenant_id" "$AZURE_TENANT"

echo ""
echo "--- GPU CLOUDS ---"

# RunPod
echo "RunPod:"
RUNPOD_KEY=$(prompt_key "RunPod" "RUNPOD_API_KEY")
store_secret "runpod" "api_key" "$RUNPOD_KEY"

# Vast.ai
echo "Vast.ai:"
VASTAI_KEY=$(prompt_key "Vast.ai" "VASTAI_API_KEY")
store_secret "vastai" "api_key" "$VASTAI_KEY"

# Lambda Labs
echo "Lambda Labs:"
LAMBDA_KEY=$(prompt_key "Lambda Labs" "LAMBDALABS_API_KEY")
store_secret "lambdalabs" "api_key" "$LAMBDA_KEY"

# CoreWeave
echo "CoreWeave:"
COREWEAVE_KEY=$(prompt_key "CoreWeave" "COREWEAVE_API_KEY")
store_secret "coreweave" "api_key" "$COREWEAVE_KEY"

# Paperspace
echo "Paperspace:"
PAPERSPACE_KEY=$(prompt_key "Paperspace" "PAPERSPACE_API_KEY")
store_secret "paperspace" "api_key" "$PAPERSPACE_KEY"

echo ""
echo "--- SERVERLESS INFERENCE ---"

# HuggingFace
echo "HuggingFace:"
HF_KEY=$(prompt_key "HuggingFace" "HUGGINGFACE_API_KEY")
store_secret "huggingface" "api_key" "$HF_KEY"

# Replicate
echo "Replicate:"
REPLICATE_KEY=$(prompt_key "Replicate" "REPLICATE_API_TOKEN")
store_secret "replicate" "api_token" "$REPLICATE_KEY"

# Groq
echo "Groq:"
GROQ_KEY=$(prompt_key "Groq" "GROQ_API_KEY")
store_secret "groq" "api_key" "$GROQ_KEY"

# Cerebras
echo "Cerebras:"
CEREBRAS_KEY=$(prompt_key "Cerebras" "CEREBRAS_API_KEY")
store_secret "cerebras" "api_key" "$CEREBRAS_KEY"

# Together AI
echo "Together AI:"
TOGETHER_KEY=$(prompt_key "Together AI" "TOGETHER_API_KEY")
store_secret "together" "api_key" "$TOGETHER_KEY"

# Fireworks AI
echo "Fireworks AI:"
FIREWORKS_KEY=$(prompt_key "Fireworks AI" "FIREWORKS_API_KEY")
store_secret "fireworks" "api_key" "$FIREWORKS_KEY"

# OpenRouter
echo "OpenRouter:"
OPENROUTER_KEY=$(prompt_key "OpenRouter" "OPENROUTER_API_KEY")
store_secret "openrouter" "api_key" "$OPENROUTER_KEY"

# DeepInfra
echo "DeepInfra:"
DEEPINFRA_KEY=$(prompt_key "DeepInfra" "DEEPINFRA_API_KEY")
store_secret "deepinfra" "api_key" "$DEEPINFRA_KEY"

echo ""
echo "--- INTERNAL SERVICES ---"

# Database
echo "Database credentials:"
store_secret "database" "postgres_password" "${POSTGRES_PASSWORD:-gpubroker_dev_pass}"
store_secret "database" "redis_password" "${REDIS_PASSWORD:-}"
store_secret "database" "clickhouse_password" "${CLICKHOUSE_PASSWORD:-gpubroker_dev_pass}"

# JWT
echo "JWT Secret:"
store_secret "auth" "jwt_secret" "${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"

echo ""
echo "============================================"
echo "✅ Secrets stored in Vault!"
echo ""
echo "To verify, run:"
echo "  vault kv list secret/gpubroker/"
echo "============================================"
