#!/bin/sh
set -e

# Run Alembic migrations using uv
echo "Running database migrations..."
uv run alembic upgrade head

# Execute the main application using uv
echo "Starting application..."
exec uv run python main.py
