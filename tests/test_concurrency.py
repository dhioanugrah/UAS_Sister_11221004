import httpx
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

def event(topic, event_id):
    return {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "race",
        "payload": {"n": 1},
    }

def test_parallel_duplicate_still_one(client: httpx.Client, base_url: str):
    eid = "EVT-RACE-DUP-00000001"
    body = {"events":[event("billing", eid)]}

    def send():
        return httpx.post(f"{base_url}/publish", json=body, timeout=10.0).status_code

    with ThreadPoolExecutor(max_workers=30) as ex:
        codes = list(ex.map(lambda _: send(), range(200)))
    assert all(c == 200 for c in codes)

    time.sleep(2)
    r = client.get(f"{base_url}/events", params={"topic":"billing"}).json()
    assert len([x for x in r if x["event_id"] == eid]) == 1

def test_parallel_unique_count_increases(client, base_url):
    base = "EVT-RACE-UNIQ-"
    bodies = [{"events":[event("inventory", f"{base}{i:06d}")]} for i in range(100)]

    def send(b):
        return httpx.post(f"{base_url}/publish", json=b, timeout=10.0).status_code

    with ThreadPoolExecutor(max_workers=30) as ex:
        codes = list(ex.map(send, bodies))
    assert all(c == 200 for c in codes)

    time.sleep(2)
    r = client.get(f"{base_url}/events", params={"topic":"inventory"}).json()
    # minimal check: harus >= 100 item unik dari batch ini
    hits = [x for x in r if x["event_id"].startswith(base)]
    assert len(hits) >= 100
