import os, random, uuid, requests
from datetime import datetime, timezone

TARGET = os.environ["TARGET_URL"]

def make_event(topic: str, event_id: str):
    return {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "publisher",
        "payload": {"msg": "hello", "rand": random.randint(1, 999999)}
    }

def main():
    topics = ["auth", "billing", "inventory", "ops"]
    unique_pool = []

    total = int(os.getenv("TOTAL", "20000"))
    dup_ratio = float(os.getenv("DUP_RATIO", "0.35"))

    for _ in range(total):
        if unique_pool and random.random() < dup_ratio:
            event_id = random.choice(unique_pool)
        else:
            event_id = str(uuid.uuid4())
            unique_pool.append(event_id)

        ev = make_event(random.choice(topics), event_id)
        requests.post(TARGET, json={"events": [ev]}, timeout=5)

    print("done")

if __name__ == "__main__":
    main()
