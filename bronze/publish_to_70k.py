import json, uuid, random, time, subprocess
from datetime import datetime, timedelta
from google.cloud import pubsub_v1

PROJECT_ID  = "pipeline-health-mon-2026"
TARGET      = 70_000
BATCH_SIZE  = 1_000
MAX_BATCHES = 80
SLEEP_SECS  = 120  # segundos entre batches

TABLES_11 = [
    "customer_events", "booking_events", "payment_events", "support_events",
    "cancellation_events", "marketing_events", "itinerary_events",
    "hotel_events", "flight_events", "review_events", "search_events"
]

def now_ts():   return datetime.utcnow().isoformat() + "Z"
def rand_date(): return (datetime.utcnow() - timedelta(days=random.randint(0,365))).strftime("%Y-%m-%d")
def rand_dt():  return (datetime.utcnow() - timedelta(days=random.randint(0,365))).isoformat() + "Z"

COUNTRIES  = ["MX","US","CA","BR","AR","ES","FR","DE","GB","JP"]
CITIES     = ["Monterrey","CDMX","Toronto","NYC","London","Paris","Berlin","Tokyo"]
CURRENCIES = ["USD","MXN","EUR","CAD","BRL"]
CHANNELS   = ["web","mobile","agent","api"]
DEVICES    = ["desktop","mobile","tablet"]
STATUSES   = ["confirmed","pending","cancelled","completed"]
METHODS    = ["credit_card","debit_card","paypal","bank_transfer","crypto"]
PRIORITIES = ["low","medium","high","critical"]
CATEGORIES = ["billing","technical","general","cancellation","refund"]
SEGMENTS   = ["bronze","silver","gold","platinum"]
TIERS      = ["standard","plus","elite","elite_plus"]
AIRLINES   = ["Aeromexico","United","Delta","Lufthansa","Iberia","LATAM"]
CLASSES    = ["economy","business","first"]
ROOM_TYPES = ["single","double","suite","deluxe","penthouse"]
SERVICES   = ["flight","hotel","package","support","general"]
REASONS    = ["customer_request","schedule_change","price_drop","force_majeure"]
REFUND_ST  = ["pending","processed","denied","partial"]
CAMPAIGN_C = ["email","sms","push","social","display"]
EVT_TYPES  = ["click","open","conversion","impression","unsubscribe"]

GENERATORS = {
    "customer_events":     lambda: {"customer_id":str(uuid.uuid4()),"full_name":f"Customer {random.randint(1000,9999)}","email":f"user{random.randint(1,99999)}@example.com","phone":f"+52{random.randint(1000000000,9999999999)}","country":random.choice(COUNTRIES),"city":random.choice(CITIES),"customer_segment":random.choice(SEGMENTS),"loyalty_tier":random.choice(TIERS),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "booking_events":      lambda: {"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"booking_date":rand_date(),"travel_start_date":rand_date(),"travel_end_date":rand_date(),"booking_status":random.choice(STATUSES),"total_amount":round(random.uniform(100,5000),2),"currency":random.choice(CURRENCIES),"destination_city":random.choice(CITIES),"destination_country":random.choice(COUNTRIES),"channel":random.choice(CHANNELS),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "payment_events":      lambda: {"payment_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"payment_date":rand_date(),"payment_method":random.choice(METHODS),"payment_status":random.choice(["completed","failed","pending","refunded"]),"amount":round(random.uniform(50,5000),2),"currency":random.choice(CURRENCIES),"transaction_reference":str(uuid.uuid4()).replace("-","")[:20].upper(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "support_events":      lambda: {"ticket_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"created_date":rand_date(),"closed_date":rand_date(),"ticket_status":random.choice(["open","in_progress","closed","escalated"]),"priority":random.choice(PRIORITIES),"issue_category":random.choice(CATEGORIES),"assigned_agent":f"agent_{random.randint(1,50):03d}","resolution_time_hours":round(random.uniform(0.5,72),2),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "cancellation_events": lambda: {"cancellation_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"cancellation_date":rand_date(),"cancellation_reason":random.choice(REASONS),"refund_status":random.choice(REFUND_ST),"refund_amount":round(random.uniform(0,5000),2),"currency":random.choice(CURRENCIES),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "marketing_events":    lambda: {"campaign_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"event_date":rand_date(),"campaign_name":f"Campaign_{random.randint(100,999)}","channel":random.choice(CAMPAIGN_C),"event_type":random.choice(EVT_TYPES),"device_type":random.choice(DEVICES),"country":random.choice(COUNTRIES),"city":random.choice(CITIES),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "itinerary_events":    lambda: {"event_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"origin":random.choice(CITIES),"destination":random.choice(CITIES),"travel_date":rand_date(),"event_timestamp":rand_dt(),"ingested_at":now_ts()},
    "hotel_events":        lambda: {"hotel_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"hotel_name":f"Hotel_{random.randint(1,500)}","city":random.choice(CITIES),"country":random.choice(COUNTRIES),"check_in_date":rand_date(),"check_out_date":rand_date(),"room_type":random.choice(ROOM_TYPES),"number_of_nights":random.randint(1,30),"total_room_amount":round(random.uniform(50,3000),2),"currency":random.choice(CURRENCIES),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "flight_events":       lambda: {"flight_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"airline":random.choice(AIRLINES),"flight_number":f"{random.choice(['AM','UA','DL','LH','IB'])}{random.randint(100,9999)}","departure_city":random.choice(CITIES),"arrival_city":random.choice(CITIES),"departure_datetime":rand_dt(),"arrival_datetime":rand_dt(),"ticket_class":random.choice(CLASSES),"ticket_amount":round(random.uniform(80,4000),2),"currency":random.choice(CURRENCIES),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "review_events":       lambda: {"review_id":str(uuid.uuid4()),"booking_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"review_date":rand_date(),"rating":random.randint(1,5),"review_title":f"Review {random.randint(1,9999)}","review_comment":f"Comment {random.randint(1,9999)}","service_category":random.choice(SERVICES),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
    "search_events":       lambda: {"search_id":str(uuid.uuid4()),"customer_id":str(uuid.uuid4()),"search_date":rand_date(),"origin_city":random.choice(CITIES),"destination_city":random.choice(CITIES),"destination_country":random.choice(COUNTRIES),"travel_start_date":rand_date(),"travel_end_date":rand_date(),"number_of_guests":random.randint(1,10),"device_type":random.choice(DEVICES),"created_at":rand_dt(),"updated_at":rand_dt(),"ingested_at":now_ts()},
}

def get_counts():
    union = "\nUNION ALL ".join(
        f"SELECT '{t}' AS tabla, COUNT(*) AS n FROM `{PROJECT_ID}.bronze.{t}`"
        for t in TABLES_11
    )
    r = subprocess.run(
        ["bq","query","--use_legacy_sql=false","--format=json",
         f"SELECT tabla, n FROM ({union}) ORDER BY tabla"],
        capture_output=True, text=True
    )
    return {row["tabla"]: int(row["n"]) for row in json.loads(r.stdout)}

def log(msg):
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    log("=== publish_to_70k.py INICIADO ===")

    # Consultar conteos actuales
    log("Consultando conteos en BQ...")
    counts = get_counts()

    log("\n📊 Estado actual:")
    needs = {}
    for tabla in sorted(counts, key=lambda t: counts[t]):
        current = counts[tabla]
        needed  = max(0, TARGET - current)
        batches = min(MAX_BATCHES, (needed + BATCH_SIZE - 1) // BATCH_SIZE)
        estado  = "✅ YA COMPLETA" if needed == 0 else f"🔄 faltan {needed:,} → {batches} batches"
        log(f"  {tabla:<25} {current:>7,}  {estado}")
        if needed > 0:
            needs[tabla] = {"needed": needed, "batches": batches}

    if not needs:
        log("✅ Todas las tablas ya tienen 70K+. Nada que publicar.")
        return

    total_msgs   = sum(min(v["batches"] * BATCH_SIZE, v["needed"]) for v in needs.values())
    max_batches  = max(v["batches"] for v in needs.values())
    eta_min      = (max_batches * SLEEP_SECS) // 60
    log(f"\n📦 Mensajes a publicar: {total_msgs:,}")
    log(f"⏱  ETA estimado: ~{eta_min} minutos ({max_batches} batches × {SLEEP_SECS}s)\n")

    publisher = pubsub_v1.PublisherClient()
    topics = {
        tabla: publisher.topic_path(PROJECT_ID, tabla.replace("_", "-"))
        for tabla in needs
    }

    total_pub = 0
    for b in range(max_batches):
        batch_futures = []
        for tabla, info in needs.items():
            if b >= info["batches"]:
                continue
            gen = GENERATORS[tabla]
            for _ in range(BATCH_SIZE):
                msg = json.dumps(gen()).encode("utf-8")
                batch_futures.append(publisher.publish(topics[tabla], msg))

        for f in batch_futures:
            f.result()

        total_pub += len(batch_futures)
        log(f"✅ Batch {b+1}/{max_batches} completado — {total_pub:,} mensajes publicados total")

        if b < max_batches - 1:
            log(f"   💤 Durmiendo {SLEEP_SECS}s...")
            time.sleep(SLEEP_SECS)

    log(f"\n🎉 Publisher finalizado — {total_pub:,} mensajes publicados")
    log("Espera ~5 min y verifica conteos en BQ.")

if __name__ == "__main__":
    main()
