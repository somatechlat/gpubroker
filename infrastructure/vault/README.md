# HashiCorp Vault - GPUBROKER Secret Management

## Overview

All sensitive credentials (API keys, passwords, tokens) MUST be stored in HashiCorp Vault.

**NEVER:**
- Commit API keys to git
- Store secrets in environment variables
- Hardcode credentials in code
- Create files containing secrets

## Quick Start

### 1. Start Vault

```bash
minikube start -p gpubroker --driver=vfkit --container-runtime=containerd --disk=10g --memory=8g --cpus=4 --addons=ingress
tilt up
```

Vault runs in dev mode for local development and does not require manual unseal.

### 2. Store Your API Keys

```bash
kubectl -n gpubrokernamespace exec -it deploy/vault -- /vault/scripts/store-secrets.sh
```

Or manually via UI at http://localhost:28006 (port-forwarded by Tilt)

### 3. Configure Services

Add to your `.env`:
```bash
VAULT_ADDR=http://vault:18280
VAULT_ROLE_ID=<from /vault/config/approle-role-id.txt>
VAULT_SECRET_ID=<from /vault/config/approle-secret-id.txt>
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GPUBROKER Services                    │
├─────────────────────────────────────────────────────────┤
│                   Django 5 Backend                       │
│  ┌─────────────┬─────────────┬─────────────────────┐    │
│  │  auth_app   │  providers  │  kpi / math_core    │    │
│  └─────────────┴─────────────┴─────────────────────┘    │
│                            │                            │
│                    ┌───────▼───────┐                    │
│                    │  VaultClient  │                    │
│                    │  (AppRole)    │                    │
│                    └───────┬───────┘                    │
└────────────────────────────┼────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  HashiCorp Vault │
                    │                  │
                    │  secret/gpubroker/│
                    │  ├── runpod/     │
                    │  ├── vastai/     │
                    │  ├── aws/        │
                    │  ├── google/     │
                    │  └── ...         │
                    └──────────────────┘
```

## Secret Paths

| Provider | Path | Keys |
|----------|------|------|
| RunPod | `secret/gpubroker/runpod` | `api_key` |
| Vast.ai | `secret/gpubroker/vastai` | `api_key` |
| AWS | `secret/gpubroker/aws` | `access_key_id`, `secret_access_key` |
| Google | `secret/gpubroker/google` | `api_key`, `service_account_json` |
| Azure | `secret/gpubroker/azure` | `client_id`, `client_secret`, `tenant_id` |
| HuggingFace | `secret/gpubroker/huggingface` | `api_key` |
| Replicate | `secret/gpubroker/replicate` | `api_token` |
| Groq | `secret/gpubroker/groq` | `api_key` |
| Database | `secret/gpubroker/database` | `postgres_password`, `redis_password` |
| Auth | `secret/gpubroker/auth` | `jwt_private_key`, `jwt_public_key` |

## Usage in Code

```python
from shared.vault_client import VaultClient, get_secret

# Option 1: Singleton
api_key = get_secret("runpod", "api_key")

# Option 2: Instance
vault = VaultClient()
api_key = vault.get_secret("runpod", "api_key")

# Get all secrets for a provider
secrets = vault.get_provider_secrets("aws")
access_key = secrets["access_key_id"]
secret_key = secrets["secret_access_key"]
```

## Production Considerations

1. **High Availability**: Use Consul or Raft storage backend
2. **TLS**: Enable TLS for all Vault communication
3. **Auto-Unseal**: Configure AWS KMS, Azure Key Vault, or GCP KMS
4. **Audit Logging**: Enable audit device for compliance
5. **Key Rotation**: Implement regular secret rotation
6. **Backup**: Regular backup of Vault data

## Troubleshooting

### Vault is sealed
```bash
# Get unseal keys from secure storage
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

### Cannot authenticate
```bash
# Check AppRole credentials
vault read auth/approle/role/gpubroker-service/role-id
vault write -f auth/approle/role/gpubroker-service/secret-id
```

### Secret not found
```bash
# List secrets
vault kv list secret/gpubroker/

# Read a secret
vault kv get secret/gpubroker/runpod
```

## Security Checklist

- [ ] Unseal keys distributed to different people
- [ ] Root token stored securely (not in code/git)
- [ ] TLS enabled in production
- [ ] Audit logging enabled
- [ ] AppRole secret IDs rotated regularly
- [ ] No secrets in environment variables
- [ ] No secrets in git history
