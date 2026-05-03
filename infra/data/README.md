# Infraestructura — Travel Analytics Platform

Terraform para provisionar los recursos GCP del proyecto.

## Recursos creados

| Recurso | Nombre |
|---|---|
| Pub/Sub Topic | `crm-events` |
| Pub/Sub Subscription | `crm-events-sub` |
| BigQuery Dataset | `bronze`, `silver`, `gold` |
| GCS Bucket | `{project_id}-bronze`, `{project_id}-silver`, `{project_id}-gold` |
| Service Account | `pipeline-sa` |

## Uso

```bash
cd infra/

# 1. Inicializar Terraform
terraform init

# 2. Revisar los recursos a crear
terraform plan -var="project_id=TU_PROJECT_ID"

# 3. Aplicar
terraform apply -var="project_id=TU_PROJECT_ID"

# 4. Exportar credenciales
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/keys/pipeline-sa.json"
```

## Notas

- El archivo `keys/pipeline-sa.json` se genera localmente y **no se commitea**.
- Los buckets tienen `force_destroy = true` para facilitar el teardown en demo; quitar en producción.
