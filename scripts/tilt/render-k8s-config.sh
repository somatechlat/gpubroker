#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAMESPACE="gpubrokernamespace"
CURRENT_CONTEXT="$(kubectl config current-context 2>/dev/null || true)"

if [[ "${CURRENT_CONTEXT}" != "gpubroker" ]]; then
  echo "Refusing to apply configs outside the gpubroker context (current: ${CURRENT_CONTEXT:-unknown})." >&2
  exit 1
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env var: ${name}" >&2
    exit 1
  fi
}

require_key_or_file() {
  local name="$1"
  local file_var="${name}_FILE"
  if [[ -n "${!file_var:-}" ]]; then
    if [[ ! -f "${!file_var}" ]]; then
      echo "${file_var} points to a missing file: ${!file_var}" >&2
      exit 1
    fi
    return 0
  fi
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env var: ${name} (or ${file_var})" >&2
    exit 1
  fi
}

require_env POSTGRES_PASSWORD
require_env CLICKHOUSE_PASSWORD
require_env DJANGO_SECRET_KEY
require_key_or_file JWT_PRIVATE_KEY
require_key_or_file JWT_PUBLIC_KEY
require_env GRAFANA_PASSWORD
require_env SPICEDB_KEY
require_env AIRFLOW__CORE__FERNET_KEY
require_env AIRFLOW_ADMIN_PASSWORD
require_env VAULT_TOKEN

# Override DATABASE_URL for K8s - always use internal service name
DATABASE_URL="postgresql://gpubroker:${POSTGRES_PASSWORD}@postgres:5432/gpubroker"
CLICKHOUSE_URL="${CLICKHOUSE_URL:-http://gpubroker:${CLICKHOUSE_PASSWORD}@clickhouse:8123/gpubroker_analytics}"
AIRFLOW_DB_URL="${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-postgresql+psycopg2://gpubroker:${POSTGRES_PASSWORD}@postgres:5432/gpubroker}"
SPICEDB_DATASTORE_CONN_URI="${SPICEDB_DATASTORE_CONN_URI:-postgres://gpubroker:${POSTGRES_PASSWORD}@postgres:5432/gpubroker?sslmode=disable}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

JWT_PRIVATE_PATH="${TMP_DIR}/jwt_private_key"
JWT_PUBLIC_PATH="${TMP_DIR}/jwt_public_key"

if [[ -n "${JWT_PRIVATE_KEY_FILE:-}" ]]; then
  JWT_PRIVATE_PATH="${JWT_PRIVATE_KEY_FILE}"
else
  printf '%s' "${JWT_PRIVATE_KEY}" > "${JWT_PRIVATE_PATH}"
fi

if [[ -n "${JWT_PUBLIC_KEY_FILE:-}" ]]; then
  JWT_PUBLIC_PATH="${JWT_PUBLIC_KEY_FILE}"
else
  printf '%s' "${JWT_PUBLIC_KEY}" > "${JWT_PUBLIC_PATH}"
fi

cat <<EOF_NAMESPACE
apiVersion: v1
kind: Namespace
metadata:
  name: ${NAMESPACE}
EOF_NAMESPACE

echo "---"

kubectl create configmap gpubroker-nginx-config \
  --namespace "${NAMESPACE}" \
  --from-file=nginx.conf="${ROOT_DIR}/infrastructure/nginx/nginx.conf" \
  --dry-run=client -o yaml

echo "---"

kubectl create configmap gpubroker-prometheus-config \
  --namespace "${NAMESPACE}" \
  --from-file=prometheus.yml="${ROOT_DIR}/infrastructure/prometheus/prometheus.yml" \
  --dry-run=client -o yaml

echo "---"

kubectl create configmap gpubroker-grafana-datasources \
  --namespace "${NAMESPACE}" \
  --from-file=datasources.yml="${ROOT_DIR}/infrastructure/grafana/datasources/datasources.yml" \
  --dry-run=client -o yaml

echo "---"

kubectl create configmap gpubroker-grafana-dashboards \
  --namespace "${NAMESPACE}" \
  --from-file=dashboards.yml="${ROOT_DIR}/infrastructure/grafana/dashboards/dashboards.yml" \
  --dry-run=client -o yaml

echo "---"

kubectl create configmap gpubroker-vault-config \
  --namespace "${NAMESPACE}" \
  --from-file=vault.hcl="${ROOT_DIR}/infrastructure/vault/config/vault.hcl" \
  --dry-run=client -o yaml

echo "---"

kubectl create configmap gpubroker-vault-scripts \
  --namespace "${NAMESPACE}" \
  --from-file="${ROOT_DIR}/infrastructure/vault/scripts" \
  --dry-run=client -o yaml

echo "---"

kubectl create secret generic gpubroker-secrets \
  --namespace "${NAMESPACE}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD}" \
  --from-literal=DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}" \
  --from-literal=DATABASE_URL="${DATABASE_URL}" \
  --from-literal=CLICKHOUSE_URL="${CLICKHOUSE_URL}" \
  --from-file=JWT_PRIVATE_KEY="${JWT_PRIVATE_PATH}" \
  --from-file=JWT_PUBLIC_KEY="${JWT_PUBLIC_PATH}" \
  --from-literal=GRAFANA_PASSWORD="${GRAFANA_PASSWORD}" \
  --from-literal=SPICEDB_GRPC_PRESHARED_KEY="${SPICEDB_KEY}" \
  --from-literal=SPICEDB_DATASTORE_CONN_URI="${SPICEDB_DATASTORE_CONN_URI}" \
  --from-literal=AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="${AIRFLOW_DB_URL}" \
  --from-literal=AIRFLOW__CORE__FERNET_KEY="${AIRFLOW__CORE__FERNET_KEY}" \
  --from-literal=AIRFLOW_ADMIN_PASSWORD="${AIRFLOW_ADMIN_PASSWORD}" \
  --from-literal=VAULT_TOKEN="${VAULT_TOKEN}" \
  --dry-run=client -o yaml
