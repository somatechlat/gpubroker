#!/bin/bash
# GPUBROKER Django Development Server Startup Script

export DJANGO_SETTINGS_MODULE=config.settings.development
export DATABASE_URL=${DATABASE_URL:-postgresql://gpubroker:gpubroker_dev_password@localhost:28001/gpubroker_dev}
export REDIS_URL=${REDIS_URL:-redis://localhost:28004/0}

echo "Starting Django development server on port 10355..."
python3 manage.py runserver 0.0.0.0:10355
