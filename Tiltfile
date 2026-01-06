# GPUBROKER Tiltfile (Minikube + Kubernetes)

load('ext://restart_process', 'docker_build_with_restart')

k8s_yaml(local('./scripts/tilt/render-k8s-config.sh'))
k8s_yaml('infrastructure/k8s/local-prod.yaml')

docker_build_with_restart(
    'gpubroker-backend',
    './backend/gpubroker',
    entrypoint=['/docker-entrypoint.sh', 'daphne', '-b', '0.0.0.0', '-p', '8000', 'config.asgi:application'],
    live_update=[
        fall_back_on(['backend/gpubroker/requirements.txt']),
        sync('./backend/gpubroker', '/app'),
    ],
)

docker_build(
    'gpubroker-frontend',
    './frontend',
    dockerfile='./frontend/Dockerfile',
    live_update=[
        fall_back_on(['frontend/package.json', 'frontend/bun.lock', 'frontend/package-lock.json']),
        sync('./frontend/src', '/app/src'),
        sync('./frontend/index.html', '/app/index.html'),
        sync('./frontend/vite.config.ts', '/app/vite.config.ts'),
        sync('./frontend/tailwind.config.ts', '/app/tailwind.config.ts'),
        sync('./frontend/postcss.config.js', '/app/postcss.config.js'),
    ],
)

k8s_resource('nginx', port_forwards=[port_forward(28080, 80)])
k8s_resource('prometheus', port_forwards=[port_forward(28008, 9090)])
k8s_resource('grafana', port_forwards=[port_forward(28009, 3000)])
k8s_resource('airflow-webserver', port_forwards=[port_forward(28010, 8080)])
k8s_resource('flink-jobmanager', port_forwards=[port_forward(28011, 8081)])
k8s_resource('vault', port_forwards=[port_forward(28006, 18280)])
