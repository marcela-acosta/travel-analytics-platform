import os
import ssl
import certifi

CA_FILE = certifi.where()

os.environ["SSL_CERT_FILE"] = CA_FILE
os.environ["REQUESTS_CA_BUNDLE"] = CA_FILE
os.environ["CURL_CA_BUNDLE"] = CA_FILE
os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = CA_FILE
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

ssl._create_default_https_context = lambda *args, **kwargs: ssl.create_default_context(
    cafile=CA_FILE
)

import json  # noqa: E402
import logging  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import apache_beam as beam  # noqa: E402
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions  # noqa: E402

PROJECT_ID = "pipeline-health-mon-2026"
SUBSCRIPTION = f"projects/{PROJECT_ID}/subscriptions/crm-events-sub"
BQ_TABLE = f"{PROJECT_ID}:bronze.crm_events"

SCHEMA = (
    "opportunity_id:STRING,"
    "stage:STRING,"
    "agent_id:STRING,"
    "product:STRING,"
    "value:FLOAT,"
    "region:STRING,"
    "expected_close_date:STRING,"
    "updated_at:STRING,"
    "ingested_at:TIMESTAMP"
)


def parse_message(msg):
    try:
        data = json.loads(msg.decode("utf-8"))
        data["ingested_at"] = datetime.now(timezone.utc).isoformat()

        required_fields = [
            "opportunity_id",
            "stage",
            "agent_id",
            "product",
            "value",
            "region",
            "expected_close_date",
            "updated_at",
            "ingested_at",
        ]

        if not all(field in data for field in required_fields):
            logging.error("Missing required fields in message: %s", data)
            return None

        return data

    except Exception as e:
        logging.error("Error parsing message: %s", e)
        return None


def run():
    logging.getLogger().setLevel(logging.INFO)

    options = PipelineOptions()
    options.view_as(StandardOptions).runner = "DirectRunner"
    options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=options) as p:
        (
            p
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(subscription=SUBSCRIPTION)
            | "ParseMessage" >> beam.Map(parse_message)
            | "FilterNulls" >> beam.Filter(lambda x: x is not None)
            | "WriteToBigQuery"
            >> beam.io.WriteToBigQuery(
                table=BQ_TABLE,
                schema=SCHEMA,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )


if __name__ == "__main__":
    run()
