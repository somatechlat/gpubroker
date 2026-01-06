# GPUBROKER - Live Deployment Guide

## Local Production-Like (Minikube + Tilt)

### Step 1 - Prepare Minikube Build Context
```bash
minikube status
# Use Minikube's Docker daemon for image builds
# (see https://minikube.sigs.k8s.io/docs/handbook/pushing/)
eval $(minikube docker-env)
```

### Step 2 - Export Required Secrets (No Secrets in Repo)
```bash
export POSTGRES_PASSWORD=...
export CLICKHOUSE_PASSWORD=...
export DJANGO_SECRET_KEY=...
export JWT_PRIVATE_KEY=...                # or set JWT_PRIVATE_KEY_FILE
export JWT_PUBLIC_KEY=...                 # or set JWT_PUBLIC_KEY_FILE
export GRAFANA_PASSWORD=...
export SPICEDB_KEY=...
export AIRFLOW__CORE__FERNET_KEY=...
export AIRFLOW_ADMIN_PASSWORD=...
```

Optional:
```bash
export AIRFLOW_ADMIN_USER=admin
export DATABASE_URL=...
export CLICKHOUSE_URL=...
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=...
export SPICEDB_DATASTORE_CONN_URI=...
```

### Step 3 - Start Tilt
```bash
tilt up
```

Tilt applies Kubernetes manifests from `infrastructure/k8s/local-prod.yaml` and generates
namespace/configmaps/secrets via `scripts/tilt/render-k8s-config.sh`.

### Step 4 - Verify Endpoints (Port-Forwards)
- `http://localhost:28080` (Nginx + frontend + API)
- `http://localhost:28080/api/v2/docs` (Django Ninja API docs)
- `http://localhost:28009` (Grafana)
- `http://localhost:28008` (Prometheus)
- `http://localhost:28010` (Airflow UI)
- `http://localhost:28011` (Flink UI)
- `http://localhost:28006` (Vault UI, optional)

## Current Capabilities

### Adapters Implemented in Repo
- RunPod
- Vast.ai

The provider registry lists additional names, but those adapter modules are not present in this repo and are skipped at runtime.
Adapters return live pricing once provider API keys are configured via `/config/integrations` or environment variables.

### Exposed Endpoints
- `/providers` — paginated offers with filters
- `/config/integrations` — list/save provider credentials (stored in user preferences)
- `/health` — service health checks
- WebSocket gateway at `/ws` for price broadcasts (consumes Redis Pub/Sub `price_updates`)

### Data Sources
- Provider pricing is fetched from upstream APIs at runtime; availability depends on supplied credentials and provider uptime.

## Monitoring
- **Prometheus**: `http://localhost:28008`
- **Grafana**: `http://localhost:28009`

## Troubleshooting

### Common Issues
1. **Secret/Env Issues**: `scripts/tilt/render-k8s-config.sh` fails if required env vars are missing.
2. **Image Build Issues**: Re-run `eval $(minikube docker-env)` before `tilt up`.
3. **Port Conflicts**: Adjust `port_forward(...)` values in `Tiltfile`.
4. **Vault**: Vault is deployed but not initialized by default; initialize via Vault CLI before enabling `VAULT_ENABLED`.

## Scaling
- Kubernetes manifests live in `infrastructure/k8s/local-prod.yaml` and are applied by Tilt for local production-like testing.
