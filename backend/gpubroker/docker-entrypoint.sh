#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
max_attempts=30
attempt=0
while ! python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection()" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "Database connection failed after $max_attempts attempts"
        exit 1
    fi
    echo "Database not ready, waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done
echo "Database is ready!"

# Run migrations (fake if tables already exist)
echo "Running database migrations..."
python manage.py migrate --fake-initial --noinput 2>&1 || {
    echo "Migration with --fake-initial failed, trying --fake..."
    python manage.py migrate --fake --noinput 2>&1 || {
        echo "Warning: Migrations failed, continuing anyway..."
    }
}

# Collect static files for Nginx/Django to serve
echo "Collecting static files..."
python manage.py collectstatic --noinput 2>&1 || {
    echo "Warning: collectstatic failed, continuing anyway..."
}

# Execute the main command
exec "$@"
