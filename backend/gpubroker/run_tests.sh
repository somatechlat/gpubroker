#!/bin/bash
# Run Django tests with pytest

set -e

cd "$(dirname "$0")"

# Set Django settings module
export DJANGO_SETTINGS_MODULE=gpubroker.settings.test

# Run pytest with coverage
python -m pytest \
    --tb=short \
    -v \
    --cov=apps \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    "$@"

echo ""
echo "Coverage report generated in htmlcov/index.html"
