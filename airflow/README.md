# Airflow on team-vm

Apache Airflow 2.10 running in Docker on the shared GCP VM.

## Architecture

- **Executor**: LocalExecutor (no Celery, no Redis — keeps memory low)
- **Database**: PostgreSQL 15 (runs as a container, data persists in a Docker volume)
- **Web UI**: `http://localhost:8080` (accessed via IAP tunnel, not public)

## Accessing the Airflow UI

From your laptop, open an IAP tunnel to the VM:

```bash
gcloud compute start-iap-tunnel team-vm 8080 \
  --local-host-port=localhost:8080 \
  --zone=us-central1-a \
  --project=pipeline-health-mon-2026
```

Leave that terminal open, then in your browser:

- URL: http://localhost:8080
- User: `admin`
- Password: `admin`

**Change the password on first login.**

## Common operations (SSH into the VM first)

```bash
# SSH into the VM
gcloud compute ssh team-vm --zone us-central1-a --tunnel-through-iap

# Inside the VM:
cd /opt/travel-analytics-platform/airflow

# Check service status
sudo docker compose ps

# View logs (webserver)
sudo docker compose logs -f airflow-web

# Restart everything
sudo docker compose restart

# Pull latest DAGs (after someone pushes to main)
cd /opt/travel-analytics-platform && sudo git pull
cd airflow && sudo docker compose restart airflow-sched airflow-web
```

## Adding DAGs

Drop your `.py` files into `dags/`, push to main, then on the VM:

```bash
cd /opt/travel-analytics-platform && sudo git pull
```

The scheduler picks them up automatically — no restart needed for new DAGs.
