# Architecture Pricing Estimate

Region: **us-central1**. All prices in USD. Estimates reflect a **dev/demo workload**
(5-person team, ~1 event/min per topic, daily dbt batch, Streamlit used on-demand).

---

## GCP Components

### Compute Engine — Shared VM (Airflow + dbt + Streamlit)

| Spec | Rate | Assumed usage | Monthly est. |
|------|------|---------------|-------------|
| e2-standard-8 (8 vCPU / 32 GB) | $0.2683/hr on-demand | ~8 h/day active (vm-idle-checker stops VM when CPU < 5%) | **~$64** |
| Boot disk 30 GB SSD | $0.17/GB/month | 30 GB | **~$5** |
| Static IP (reserved) | $0.010/hr when VM is stopped | ~16 h/day stopped | **~$5** |

> Switch to a **committed-use 1-year contract** to reduce the VM rate to ~$0.162/hr → saves ~$30/month.
> For production, consider a dedicated VM per service (Airflow, Streamlit) or migrating Streamlit to Cloud Run.

---

### Apache Beam / Dataflow

| Runner | Spec | Monthly est. |
|--------|------|-------------|
| **Direct Runner** (current, on shared VM) | Included in VM cost | $0 extra |
| Dataflow Runner (if migrated) | 1 worker: 1 vCPU + 4 GB, streaming 24/7 | ~$55 |

> The current setup runs Beam on the shared VM (Direct Runner). Migrating to Dataflow would
> add ~$55/month but provides autoscaling, managed shuffle, and fault tolerance at scale.

---

### Pub/Sub

| Metric | Estimate |
|--------|----------|
| Volume | 15 topics × 1 msg/min × 500 B avg = ~320 MB/month |
| Free tier | 10 GB/month |
| **Cost** | **$0** (well within free tier) |

---

### BigQuery

| Item | Rate | Estimate | Monthly est. |
|------|------|----------|-------------|
| Active storage (bronze + silver + gold) | $0.020/GB/month | ~15 GB | **~$0.30** |
| Long-term storage (Elementary tables) | $0.010/GB/month | ~5 GB | **~$0.05** |
| On-demand queries (dbt daily runs) | $5/TB processed | ~2 GB/day × 30 = ~60 GB | **~$0.30** |
| **Subtotal** | | | **~$0.65** |

> dbt models use `SELECT *` from staging views — ensure silver and gold models reference only
> the columns they need to avoid full-table scans as data grows.
> At 100 GB/day query volume (production scale) cost becomes ~$15/month.

---

### Cloud Storage (GCS)

| Use | Rate | Estimate | Monthly est. |
|-----|------|----------|-------------|
| dbt artifacts (target/, logs) | $0.020/GB/month | ~1 GB | **~$0.02** |
| Beam staging / temp files | $0.020/GB/month | ~2 GB | **~$0.04** |
| Class A operations (writes) | $0.05/10K | minimal | **~$0.01** |
| **Subtotal** | | | **~$0.07** |

---

### Cloud Run (vm-idle-checker job)

| Metric | Estimate |
|--------|----------|
| Executions | 48/day × 30 = 1,440/month |
| CPU-seconds | ~10 s/execution × 1,440 = 14,400 CPU-s |
| Free tier | 180,000 CPU-s/month |
| **Cost** | **$0** (free tier) |

---

### Cloud Scheduler

| Metric | Estimate |
|--------|----------|
| Jobs | 1 (vm-idle-check every 30 min) |
| Free tier | 3 jobs/month |
| **Cost** | **$0** (free tier) |

---

### Artifact Registry

| Item | Rate | Estimate | Monthly est. |
|------|------|----------|-------------|
| Docker storage | $0.10/GB/month | ~0.5 GB (checker image) | **~$0.05** |

---

### Secret Manager

| Item | Estimate |
|------|----------|
| Secrets | 1 (GitHub deploy key) |
| Free tier | 6 active secret versions/month |
| **Cost** | **$0** (free tier) |

---

## OpenAI API (gpt-4o-mini)

Used by `dashboard/agent.py` to answer natural-language queries over BigQuery gold tables.

| Metric | Rate | Estimate | Monthly est. |
|--------|------|----------|-------------|
| Input tokens | $0.150/1M tokens | ~1,500 tokens/query | |
| Output tokens | $0.600/1M tokens | ~300 tokens/query | |
| **Cost per query** | | | **~$0.0004** |
| 200 queries/month | | | **~$0.08** |
| 1,000 queries/month | | | **~$0.40** |

> Cost is negligible at this scale. Even at 10,000 queries/month the cost stays under $4.
> If switching to Claude (Anthropic API), comparable pricing applies with claude-haiku-4-5
> (~$0.0008/query at similar token counts).

---

## Monthly Total Summary

| Component | Dev/demo est. |
|-----------|--------------|
| GCE VM (e2-standard-8, ~8h/day) | $64 |
| VM disk + static IP | $10 |
| Dataflow (Direct Runner, no extra cost) | $0 |
| Pub/Sub | $0 |
| BigQuery | $1 |
| GCS | $0.10 |
| Cloud Run + Scheduler + Artifact Registry | $0.05 |
| Secret Manager | $0 |
| OpenAI gpt-4o-mini (500 queries) | $0.20 |
| **Total** | **~$75/month** |

---

## Cost Reduction Levers

| Action | Savings |
|--------|---------|
| 1-year committed use on VM | ~$30/month |
| Stop VM overnight (vm-idle-checker already does this) | already included above |
| Migrate Streamlit to Cloud Run (scale-to-zero) | ~$10/month if VM is smaller |
| BigQuery partitioning + clustering on dbt models | reduces query cost as data grows |
| Use Spot/Preemptible VM for dev runs | cuts VM cost ~65%, but risks preemption |

---

## Production Scale Note

At production load (100+ events/min, multiple teams, hourly dbt runs, Dataflow streaming):

| Component | Production est. |
|-----------|----------------|
| GCE VM or GKE node pool (Airflow) | $150–$400/month |
| Dataflow streaming (autoscaling 2–4 workers) | $100–$200/month |
| BigQuery (storage + queries) | $50–$200/month |
| Pub/Sub (1M+ msgs/day) | $10–$40/month |
| Cloud Run (Streamlit, multi-instance) | $20–$60/month |
| **Total** | **~$330–$900/month** |
