import httpx
from datetime import datetime, timezone

def valid_event(overrides=None):
    e = {
        "topic": "ops",
        "event_id": "EVT-VALID-00000001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test",
        "payload": {"a": 1},
    }
    if overrides:
        e.update(overrides)
    return e

def test_reject_empty_events_array(client: httpx.Client, base_url: str):
    r = client.post(f"{base_url}/publish", json={"events": []})
    assert r.status_code == 422

def test_reject_missing_events_key(client, base_url):
    r = client.post(f"{base_url}/publish", json={})
    assert r.status_code == 422

def test_reject_empty_topic(client, base_url):
    payload = {"events":[valid_event({"topic": ""})]}
    r = client.post(f"{base_url}/publish", json=payload)
    assert r.status_code == 422

def test_reject_short_event_id(client, base_url):
    payload = {"events":[valid_event({"event_id":"123"})]}
    r = client.post(f"{base_url}/publish", json=payload)
    assert r.status_code == 422

def test_reject_invalid_timestamp(client, base_url):
    payload = {"events":[valid_event({"timestamp":"not-a-time"})]}
    r = client.post(f"{base_url}/publish", json=payload)
    assert r.status_code == 422
