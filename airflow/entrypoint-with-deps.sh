#!/bin/bash
set -e

# Install additional requirements if specified
if [ -n "$PIP_ADDITIONAL_REQUIREMENTS" ]; then
    echo "Installing additional pip requirements: $PIP_ADDITIONAL_REQUIREMENTS"
    pip install --no-cache-dir $PIP_ADDITIONAL_REQUIREMENTS
fi

# Execute the original Airflow entrypoint with the command
exec /usr/bin/dumb-init -- /entrypoint "$@"
