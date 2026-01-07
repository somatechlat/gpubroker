# GPUBROKER Tiltfile (Minikube + Kubernetes)

# Explicitly allow the isolated Minikube context.
allow_k8s_contexts('gpubroker')

# Disable Tilt Docker pruner since Docker is not used.
docker_prune_settings(disable=True)

k8s_yaml(local('./scripts/tilt/render-k8s-config.sh'))
k8s_yaml('infrastructure/k8s/local-prod.yaml')

MINIKUBE_PROFILE = 'gpubroker'

custom_build(
    'gpubroker-backend',
    'minikube -p %s image build -t $EXPECTED_REF -f Containerfile backend/gpubroker' % MINIKUBE_PROFILE,
    deps=['backend/gpubroker', 'backend/gpubroker/Containerfile'],
    disable_push=True,
    skips_local_docker=True,
)

custom_build(
    'gpubroker-frontend',
    'minikube -p %s image build -t $EXPECTED_REF -f Containerfile frontend' % MINIKUBE_PROFILE,
    deps=['frontend', 'frontend/Containerfile'],
    disable_push=True,
    skips_local_docker=True,
    live_update=[
        sync('frontend/src', '/app/src'),
        sync('frontend/index.html', '/app/index.html'),
        sync('frontend/vite.config.ts', '/app/vite.config.ts'),
        sync('frontend/tailwind.config.ts', '/app/tailwind.config.ts'),
        sync('frontend/postcss.config.js', '/app/postcss.config.js'),
        run('bun install', trigger=['frontend/package.json', 'frontend/bun.lock']),
    ],
)

custom_build(
    'gpubroker-clickhouse',
    'minikube -p %s image build -t $EXPECTED_REF -f Containerfile infrastructure/clickhouse' % MINIKUBE_PROFILE,
    deps=['infrastructure/clickhouse', 'infrastructure/clickhouse/Containerfile'],
    disable_push=True,
    skips_local_docker=True,
)

# Local ingress must remain on port 10355.
k8s_resource('nginx', port_forwards=[port_forward(10355, 80)], resource_deps=['django', 'frontend'])
k8s_resource('prometheus', port_forwards=[port_forward(28008, 9090)])
k8s_resource('grafana', port_forwards=[port_forward(28009, 3000)])
k8s_resource('airflow-webserver', port_forwards=[port_forward(28010, 8080)])
k8s_resource('flink-jobmanager', port_forwards=[port_forward(28011, 8081)])
k8s_resource('vault', port_forwards=[port_forward(28006, 18280)])
