#!/usr/bin/env python3
"""
Ingests mock performance CSV and publishes metrics to Kafka (performance.metrics.v1).
CSV columns: campaign,product,ratio,market,impressions,clicks,spend_cents,conversions
"""
import csv
import json
import os
from datetime import datetime, timezone
from kafka import KafkaProducer

BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "performance.metrics.v1"

def main(path: str):
    p = KafkaProducer(
        bootstrap_servers=BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        compression_type="gzip",
    )
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            imp = int(row.get("impressions", 0) or 0)
            clk = int(row.get("clicks", 0) or 0)
            spend_cents = int(row.get("spend_cents", 0) or 0)
            conv = int(row.get("conversions", 0) or 0)
            ctr = (clk / imp) if imp else 0.0
            cpc = (spend_cents / 100) / clk if clk else 0.0
            cpa = (spend_cents / 100) / conv if conv else 0.0
            evt = {
                "event_id": os.urandom(8).hex(),
                "ts": datetime.now(timezone.utc).isoformat(),
                "campaign_name": row.get("campaign"),
                "product": row.get("product"),
                "ratio": row.get("ratio"),
                "market": row.get("market"),
                "metrics": {
                    "impressions": imp,
                    "clicks": clk,
                    "conversions": conv,
                    "ctr": ctr,
                    "cpc": round(cpc, 4),
                    "cpa": round(cpa, 4),
                    "spend": round(spend_cents / 100, 2)
                }
            }
            p.send(TOPIC, evt)
    p.flush()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: performance_ingest.py data/samples/performance.csv")
        sys.exit(1)
    main(sys.argv[1])

