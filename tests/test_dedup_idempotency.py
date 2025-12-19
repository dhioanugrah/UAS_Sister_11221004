import httpx
import time
from datetime import datetime, timezone

def ev(topic, event_id):
    return {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test",
        "payload": {"p": "same"},
    }

def test_dedup_same_event_only_one_in_events(client: httpx.Client, base_url: str):
    eid = "EVT-DEDUP-ONE-00000001"
    payload = {"events":[ev("ops", eid)]}
    for _ in range(5):
        client.post(f"{base_url}/publish", json=payload)
    time.sleep(1)

    r = client.get(f"{base_url}/events", params={"topic":"ops"})
    items = [x for x in r.json() if x["event_id"] == eid]
    assert len(items) == 1

def test_dedup_across_batches(client, base_url):
    eid = "EVT-DEDUP-BATCH-0001"
    client.post(f"{base_url}/publish", json={"events":[ev("auth", eid), ev("auth", "EVT-DEDUP-BATCH-0002")]})
    client.post(f"{base_url}/publish", json={"events":[ev("auth", eid)]})
    time.sleep(1)

    r = client.get(f"{base_url}/events", params={"topic":"auth"})
    items = [x for x in r.json() if x["event_id"] == eid]
    assert len(items) == 1

def test_stats_invariant_received_ge_sum(client, base_url):
    s = client.get(f"{base_url}/stats").json()
    assert s["received"] >= (s["unique_processed"] + s["duplicate_dropped"])
