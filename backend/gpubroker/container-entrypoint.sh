#!/bin/bash
set -e

echo "🚀 Starting GPUBROKER Django container..."

# =============================================================================
# STEP 1: Wait for PostgreSQL to be ready
# =============================================================================
echo "⏳ Waiting for PostgreSQL..."
max_attempts=30
attempt=0

while ! python -c "
import os
import psycopg
try:
    conn = psycopg.connect(
        dbname=os.environ.get('BOOTSTRAP_DB_NAME', 'gpubroker'),
        user=os.environ.get('BOOTSTRAP_DB_USER', 'gpubroker'),
        password=os.environ.get('BOOTSTRAP_DB_PASSWORD', ''),
        host=os.environ.get('BOOTSTRAP_DB_HOST', 'postgres'),
        port=os.environ.get('BOOTSTRAP_DB_PORT', '5432'),
        connect_timeout=5
    )
    conn.close()
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ PostgreSQL connection failed after $max_attempts attempts"
        exit 1
    fi
    echo "PostgreSQL not ready, waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# =============================================================================
# STEP 2: Run database migrations
# =============================================================================
echo "📊 Running database migrations..."
python manage.py migrate --noinput 2>&1 || {
    echo "❌ Migrations failed!"
    exit 1
}
echo "✅ Migrations completed!"

# =============================================================================
# STEP 3: Initialize configuration from Vault (if not already done)
# =============================================================================
if [ -n "${VAULT_ADDR}" ] && [ -n "${VAULT_TOKEN}" ]; then
    echo "🔐 Initializing configuration from Vault..."
    bash /app/init-django-config.sh || {
        echo "⚠️  Configuration initialization failed, continuing anyway..."
    }
else
    echo "⚠️  Vault not configured, skipping configuration initialization"
fi

# =============================================================================
# STEP 4: Collect static files
# =============================================================================
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 || {
    echo "⚠️  collectstatic failed, continuing anyway..."
}
echo "✅ Static files collected!"

# =============================================================================
# STEP 5: Create superuser if needed (development only)
# =============================================================================
if [ "${DEBUG}" = "True" ] || [ "${DEBUG}" = "true" ]; then
    echo "👤 Creating superuser (development mode)..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='admin@gpubroker.local').exists():
    User.objects.create_superuser(email='admin@gpubroker.local', password='admin123', full_name='Admin User');
    print('✅ Superuser created: admin@gpubroker.local / admin123');
else:
    print('✅ Superuser already exists');
" 2>&1 || echo "⚠️  Superuser creation skipped"
fi

# =============================================================================
# STEP 6: Start the application
# =============================================================================
echo "🎯 Starting Django application..."
echo "================================================"
echo "GPUBROKER Django is ready!"
echo "================================================"

# Execute the main command
exec "$@"
