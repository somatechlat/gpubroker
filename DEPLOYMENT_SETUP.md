# 🚀 GPUBROKER - LIVE DEPLOYMENT GUIDE

## 📋 **INSTANT DEPLOYMENT CHECKLIST (SAFE, NO SECRETS IN REPO)**

### **🎯 STEP 1 - Prepare Environment**
```bash
cp .env.example .env
# Adjust ports if needed (defaults are 28000+ to avoid conflicts).
# Do NOT add API keys here.
# Required frontend targets:
#   NEXT_PUBLIC_PROVIDER_API_URL=http://localhost/api/v2/providers
#   NEXT_PUBLIC_KPI_API_URL=http://localhost/api/v2/kpi
#   NEXT_PUBLIC_AI_API_URL=http://localhost/api/v2/ai
```

### **🎯 STEP 2 - Load Secrets into Vault**
```bash
./infrastructure/vault/scripts/init-vault.sh        # once per environment
./infrastructure/vault/scripts/store-secrets.sh     # writes provider keys into Vault
```
Note: Vault client exists in the repo, but provider integrations currently read API keys from user preferences or environment variables; Vault wiring is pending.

### **🎯 STEP 3 - Start Services**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### **🎯 STEP 4 - Test Live Marketplace**
```bash
# Frontend
open http://localhost:${PORT_FRONTEND:-28030}
# API docs (Django Ninja)
open http://localhost/api/v2/docs
```

## 🔥 **CURRENT CAPABILITIES**

### **Adapters Implemented in Repo**
- RunPod
- Vast.ai

The provider registry lists additional names, but those adapter modules are not present in this repo and are skipped at runtime.
Adapters return live pricing once provider API keys are configured via `/config/integrations` or environment variables.

### **Exposed Endpoints**
- `/providers` — paginated offers with filters
- `/config/integrations` — list/save provider credentials (stored in user preferences)
- `/health` — service health checks
- WebSocket gateway at `/ws` for price broadcasts (consumes Redis Pub/Sub `price_updates`)

### **Data Sources**
- Provider pricing is fetched from upstream APIs at runtime; availability depends on supplied credentials and provider uptime.

## 📊 **MONITORING**
- **Prometheus**: http://localhost:${PORT_PROMETHEUS:-28031}
- **Grafana**: http://localhost:${PORT_GRAFANA:-28032}
Note: docker-compose.dev.yml includes a Storybook service, but `npm run storybook` is not defined in `frontend/package.json`.

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
