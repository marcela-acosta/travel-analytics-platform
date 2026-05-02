#!/bin/bash
set -e

echo ">>> Upgrading metadata database..."
superset db upgrade

echo ">>> Creating admin user..."
superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname Pipeline \
    --email admin@pipeline.com \
    --password admin123 2>/dev/null || echo "(admin already exists)"

echo ">>> Initializing roles and permissions..."
superset init

echo ">>> Done."
