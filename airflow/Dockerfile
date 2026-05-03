FROM apache/airflow:3.2.1

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir dbt-bigquery==1.9.1 astronomer-cosmos==1.8.2
