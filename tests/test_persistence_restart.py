import os, subprocess, time
import httpx
from datetime import datetime, timezone
import pytest

def e(topic, event_id):
    return {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "persist",
        "payload": {"ok": True},
    }

@pytest.mark.skipif(os.getenv("RUN_DOCKER_INTEGRATION") != "1", reason="Set RUN_DOCKER_INTEGRATION=1 to run docker restart test")
def test_persistence_after_recreate(base_url):
    client = httpx.Client(timeout=10.0)
    eid = "EVT-PERSIST-00000001"

    # publish
    r = client.post(f"{base_url}/publish", json={"events":[e("ops", eid)]})
    assert r.status_code == 200
    time.sleep(1)

    # recreate aggregator container
    subprocess.check_call(["docker", "compose", "rm", "-sf", "aggregator"])
    subprocess.check_call(["docker", "compose", "up", "-d", "aggregator"])
    time.sleep(5)

    # should still exist
    r = client.get(f"{base_url}/events", params={"topic":"ops"})
    assert any(x["event_id"] == eid for x in r.json())

    # send duplicate after restart -> still one
    client.post(f"{base_url}/publish", json={"events":[e("ops", eid)]})
    time.sleep(1)
    r = client.get(f"{base_url}/events", params={"topic":"ops"})
    assert len([x for x in r.json() if x["event_id"] == eid]) == 1
