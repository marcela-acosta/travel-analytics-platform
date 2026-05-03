#!/bin/bash
# ---------------------------------------------------------------------------
# One-time setup: generate an SSH deploy key, register it on GitHub, and
# store the private key in Google Secret Manager so the VM can clone the
# private repo on boot.
#
# Run this ONCE from your laptop (not from the VM) before the first
# `terraform apply` that uses the startup script.
#
# Prerequisites:
#   - gh CLI authenticated (gh auth login)
#   - gcloud CLI authenticated and project set to pipeline-health-mon-2026
# ---------------------------------------------------------------------------

set -euo pipefail

PROJECT_ID=pipeline-health-mon-2026
REPO=marcela-acosta/travel-analytics-platform
SECRET_NAME=github-deploy-key
KEY_PATH=$(mktemp -d)/id_ed25519

echo ">>> Enabling Secret Manager API (idempotent)"
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"

echo ">>> Generating SSH key at $KEY_PATH"
ssh-keygen -t ed25519 -C "deploy-key@team-vm" -f "$KEY_PATH" -N "" -q

echo ">>> Registering public key as GitHub deploy key (read-only)"
gh repo deploy-key add "${KEY_PATH}.pub" \
  --repo "$REPO" \
  --title "team-vm startup script"

echo ">>> Creating / updating secret in Secret Manager"
if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET_NAME" \
    --replication-policy=automatic \
    --project="$PROJECT_ID"
fi

gcloud secrets versions add "$SECRET_NAME" \
  --data-file="$KEY_PATH" \
  --project="$PROJECT_ID"

echo ">>> Cleaning up local key files"
shred -u "$KEY_PATH" "${KEY_PATH}.pub" 2>/dev/null || rm -f "$KEY_PATH" "${KEY_PATH}.pub"

echo ""
echo "Done!"
echo "  - Deploy key registered on GitHub repo: $REPO"
echo "  - Private key stored in Secret Manager secret: $SECRET_NAME"
echo ""
echo "Next step: terraform apply"
