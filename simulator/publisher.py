import json
import time
import random
import uuid
from datetime import datetime, timedelta
from google.cloud import pubsub_v1

PROJECT_ID = "pipeline-health-mon-2026"
TOPIC_ID = "crm-events"

STAGES = ["Prospección", "Calificado", "Propuesta", "Negociación", "Ganado", "Perdido"]
PRODUCTS = ["vuelo", "hotel", "auto", "paquete_2x", "paquete_3x"]
REGIONS = ["CDMX", "GDL", "MTY", "CUN", "TIJ"]

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)


def generate_event():
    return {
        "opportunity_id": str(uuid.uuid4()),
        "stage": random.choice(STAGES),
        "agent_id": f"agent_{random.randint(1, 20)}",
        "product": random.choice(PRODUCTS),
        "value": round(random.uniform(500, 15000), 2),
        "region": random.choice(REGIONS),
        "expected_close_date": (
            datetime.now() + timedelta(days=random.randint(7, 90))
        ).isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


while True:
    event = generate_event()

    message = json.dumps(event).encode("utf-8")
    future = publisher.publish(topic_path, message)
    message_id = future.result()

    print(
        f"[OK] Published message_id={message_id} opportunity_id={event['opportunity_id']}"
    )

    time.sleep(60)
