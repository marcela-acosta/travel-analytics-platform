import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
from datetime import datetime
import argparse


def parse_message(msg):
    try:
        data = json.loads(msg.decode("utf-8"))
        data["ingested_at"] = datetime.utcnow().isoformat()
        return data
    except Exception as e:
        print(f"[ERROR] Parsing message failed: {e}")
        return None


def run(subscription, table, schema):
    options = PipelineOptions(["--runner=DirectRunner", "--streaming"])

    with beam.Pipeline(options=options) as p:
        (
            p
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(subscription=subscription)
            | "ParseJSON" >> beam.Map(parse_message)
            | "FilterValidRows" >> beam.Filter(lambda x: x is not None)
            | "WriteToBigQuery"
            >> beam.io.WriteToBigQuery(
                table=table,
                schema=schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--schema", required=True)
    args, pipeline_args = parser.parse_known_args()

    run(subscription=args.subscription, table=args.table, schema=args.schema)
