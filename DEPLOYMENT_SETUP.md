# 🚀 GPUBROKER - LIVE DEPLOYMENT GUIDE

## 📋 **INSTANT DEPLOYMENT CHECKLIST (SAFE, NO SECRETS IN REPO)**

### **🎯 STEP 1 - Prepare Environment**
```bash
cp .env.example .env
# Adjust ports if needed (defaults are 28000+ to avoid conflicts).
# Do NOT add API keys here.
# Required frontend targets:
#   NEXT_PUBLIC_PROVIDER_API_URL=http://localhost:${PORT_PROVIDER:-28021}
#   NEXT_PUBLIC_KPI_API_URL=http://localhost:${PORT_KPI:-28022}
#   NEXT_PUBLIC_AI_API_URL=http://localhost:${PORT_AI_ASSISTANT:-28026}
```

### **🎯 STEP 2 - Load Secrets into Vault**
```bash
./infrastructure/vault/scripts/init-vault.sh        # once per environment
./infrastructure/vault/scripts/store-secrets.sh     # writes provider keys into Vault
```

### **🎯 STEP 3 - Start Services**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### **🎯 STEP 4 - Test Live Marketplace**
```bash
# Frontend
open http://localhost:${PORT_FRONTEND:-28030}
# Provider API docs
open http://localhost:${PORT_PROVIDER:-28021}/docs
# Keycloak admin
open http://localhost:${PORT_KEYCLOAK:-28006}
```

## 🔥 **CURRENT CAPABILITIES**

### **Adapters Available**
- AWS SageMaker, Azure ML, Google Vertex AI
- Vast.ai, RunPod, Lambda Labs, Paperspace
- Groq, Replicate, HuggingFace, CoreWeave
- IBM Watson, Oracle OCI, NVIDIA DGX
- Alibaba, Tencent, DeepInfra, Cerebras, ScaleAI, Spell, Kaggle, Run:AI
- Adapters return live pricing once provider API keys are loaded into Vault. No credentials or pricing data are bundled in the repo.

### **Exposed Endpoints**
- `/providers` — paginated offers with filters
- `/config/integrations` — list/save provider credentials (Vault-backed)
- `/health` — service health checks
- WebSocket gateway at `/ws` for price broadcasts (consumes Redis Pub/Sub `price_updates`)

### **Data Sources**
- Provider pricing is fetched from upstream APIs at runtime; availability depends on supplied credentials and provider uptime.

## 📊 **MONITORING**
- **Prometheus**: http://localhost:${PORT_PROMETHEUS:-28031}
- **Grafana**: http://localhost:${PORT_GRAFANA:-28032}
- **Storybook**: http://localhost:${PORT_STORYBOOK:-28033}

## 🛠️ **TROUBLESHOOTING**

### **Common Issues**
1. **API Key Issues**: Ensure secrets are loaded in Vault (see infrastructure/vault/scripts/store-secrets.sh) and services have VAULT_* env vars.
2. **Docker Issues**: `docker-compose down && docker-compose up --build`
3. **Port Conflicts**: Use `docker-compose --scale` to adjust
4. **Rate Limits**: Add retry logic in adapters

## 🌍 **SCALING**
- Kubernetes and Helm manifests are not included in this repository yet. Use Docker Compose for local and staging environments.

## 🎉 **NEXT STEPS**
- Load provider credentials into Vault, start the stack, and verify `/providers` returns live offers.
