Drop your GCP service-account JSON key here as `pipeline-sa.json`.

- This repository's `airflow/docker-compose.yaml` mounts this directory into the Airflow container at `/opt/airflow/keys`.
- The DAGs expect the key at `/opt/airflow/keys/pipeline-sa.json` (and `AIRFLOW_CONN_GCP_DBT` references it).
- Do NOT commit the JSON file to the repository.

Example to create a key (only run if you control the project/service account):

```
gcloud iam service-accounts keys create infra/data/keys/pipeline-sa.json \
  --iam-account=SERVICE_ACCOUNT_EMAIL@pipeline-health-mon-2026.iam.gserviceaccount.com \
  --project=pipeline-health-mon-2026
```

After placing the JSON file, restart the Airflow containers so the key and connection are available to tasks.