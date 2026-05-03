provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Pub/Sub ────────────────────────────────────────────────
resource "google_pubsub_topic" "crm_events" {
  name = "crm-events"
}

resource "google_pubsub_subscription" "crm_sub" {
  name                 = "crm-events-sub"
  topic                = google_pubsub_topic.crm_events.id
  ack_deadline_seconds = 60
}

# ── BigQuery datasets (medallion) ─────────────────────────
resource "google_bigquery_dataset" "bronze" {
  dataset_id = "bronze"
  location   = var.region
}

resource "google_bigquery_dataset" "silver" {
  dataset_id = "silver"
  location   = var.region
}

resource "google_bigquery_dataset" "gold" {
  dataset_id = "gold"
  location   = var.region
}

# ── GCS buckets (medallion) ───────────────────────────────
resource "google_storage_bucket" "bronze" {
  name          = "${var.project_id}-bronze"
  location      = var.region
  force_destroy = true
}

resource "google_storage_bucket" "silver" {
  name          = "${var.project_id}-silver"
  location      = var.region
  force_destroy = true
}

resource "google_storage_bucket" "gold" {
  name          = "${var.project_id}-gold"
  location      = var.region
  force_destroy = true
}

# ── Service Account ───────────────────────────────────────
resource "google_service_account" "pipeline_sa" {
  account_id   = "pipeline-sa"
  display_name = "Travel Analytics Platform SA"
}

resource "google_service_account_key" "pipeline_sa_key" {
  service_account_id = google_service_account.pipeline_sa.name
}

# ── IAM roles ─────────────────────────────────────────────
locals {
  sa_roles = [
    "roles/pubsub.subscriber",
    "roles/pubsub.publisher",
    "roles/bigquery.dataEditor",
    "roles/storage.objectAdmin",
  ]
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset(local.sa_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# ── Guardar key en archivo local ──────────────────────────
resource "local_file" "sa_key_file" {
  content  = base64decode(google_service_account_key.pipeline_sa_key.private_key)
  filename = "${path.module}/keys/pipeline-sa.json"
}
