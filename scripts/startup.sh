#!/bin/bash
# ---------------------------------------------------------------------------
# VM bootstrap script — runs once on first boot.
# Installs Docker, clones the project, and boots Airflow.
# ---------------------------------------------------------------------------

set -euxo pipefail

# Log everything to /var/log/startup-script.log for debugging
exec > >(tee -a /var/log/startup-script.log) 2>&1

echo "[bootstrap] Starting VM bootstrap at $(date)"

# Idempotency guard — skip if we've already run successfully
BOOTSTRAP_MARKER=/var/run/pipeline-health-bootstrapped
if [ -f "$BOOTSTRAP_MARKER" ]; then
  echo "[bootstrap] Already bootstrapped, exiting"
  exit 0
fi

PROJECT_ID=pipeline-health-mon-2026
REPO_URL=git@github.com:marcela-acosta/travel-analytics-platform.git
PROJECT_DIR=/opt/travel-analytics-platform

# --- 1. Install base packages -----------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg git jq

# --- 2. Install Docker + Docker Compose plugin ------------------------------
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# --- 3. Fetch GitHub deploy key from Secret Manager ------------------------
mkdir -p /root/.ssh
chmod 700 /root/.ssh
gcloud secrets versions access latest \
  --secret=github-deploy-key \
  --project="$PROJECT_ID" \
  > /root/.ssh/id_ed25519
chmod 600 /root/.ssh/id_ed25519

# Trust github.com host key
ssh-keyscan -H github.com >> /root/.ssh/known_hosts

# --- 4. Clone the project ---------------------------------------------------
if [ ! -d "$PROJECT_DIR" ]; then
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

# --- 5. Prepare Airflow environment -----------------------------------------
cd "$PROJECT_DIR/airflow"
mkdir -p dags logs plugins

# Write .env if it doesn't exist (copy from example, set AIRFLOW_UID)
if [ ! -f .env ]; then
  cp .env.example .env
  echo "AIRFLOW_UID=50000" >> .env
fi

# --- 6. Boot Airflow --------------------------------------------------------
docker compose up -d

# --- 7. Mark as bootstrapped ------------------------------------------------
touch "$BOOTSTRAP_MARKER"

echo "[bootstrap] Done at $(date). Airflow will be available on :8080 in ~2 min."
