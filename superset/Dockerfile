FROM apache/superset:4.1.2

USER root
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.10 \
    Flask-Cors==4.0.1 \
    sqlalchemy-bigquery==1.12.0 \
    db-dtypes==1.3.0 \
    google-cloud-bigquery-storage==2.27.0

COPY superset_config.py /app/pythonpath/superset_config.py
USER superset
