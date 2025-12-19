import httpx
import time
from datetime import datetime, timezone

def make(topic, event_id):
    return {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test",
        "payload": {"x": 1},
    }

def test_publish_single_returns_accepted(client: httpx.Client, base_url: str):
    r = client.post(f"{base_url}/publish", json={"events":[make("ops","EVT-ACCEPT-00000001")]})
    assert r.status_code == 200
    assert r.json()["accepted"] == 1

def test_get_stats_has_keys(client, base_url):
    s = client.get(f"{base_url}/stats")
    assert s.status_code == 200
    j = s.json()
    for k in ["received","unique_processed","duplicate_dropped","topics","uptime_seconds"]:
        assert k in j

def test_get_events_filter_topic(client, base_url):
    eid = "EVT-FILTER-00000001"
    client.post(f"{base_url}/publish", json={"events":[make("billing", eid)]})
    time.sleep(1)
    r = client.get(f"{base_url}/events", params={"topic":"billing"})
    assert r.status_code == 200
    assert any(x["event_id"] == eid for x in r.json())
