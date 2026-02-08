#!/bin/bash
set -e

echo "Starting Horilla HR..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "PostgreSQL is ready!"

# Run migrations
python manage.py migrate --noinput

# Compile translations
python manage.py compilemessages --ignore=.venv

# Collect static files
python manage.py collectstatic --noinput

# Load demo data on first run if LOAD_DEMO_DATA=1
if [ "${LOAD_DEMO_DATA}" = "1" ]; then
  # Check if data was already loaded (marker file)
  if [ ! -f /app/.demo_data_loaded ]; then
    echo "Loading demo data..."
    python manage.py load_demo_data
    touch /app/.demo_data_loaded
    echo "Demo data loaded!"
  else
    echo "Demo data already loaded, skipping."
  fi
fi

echo "Starting server..."
exec "$@"
