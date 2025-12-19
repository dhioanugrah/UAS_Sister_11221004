import os, json, asyncio
import redis.asyncio as redis
from .db import get_pool

STREAM = os.getenv("REDIS_STREAM", "log-events")
GROUP  = os.getenv("REDIS_GROUP", "agg-group")
CONSUMER_NAME = os.getenv("CONSUMER_NAME", "c1")

async def ensure_group(r):
    try:
        await r.xgroup_create(STREAM, GROUP, id="0-0", mkstream=True)
    except Exception:
        pass

async def process_one(pool, ev: dict) -> bool:
    topic = ev["topic"]; event_id = ev["event_id"]
    ts = ev["timestamp"]; source = ev["source"]
    payload_json = json.dumps(ev["payload"])

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE stats SET received = received + 1 WHERE id=1;")

            row = await conn.fetchrow("""
              INSERT INTO processed_events(topic, event_id)
              VALUES($1,$2)
              ON CONFLICT DO NOTHING
              RETURNING 1 AS inserted;
            """, topic, event_id)

            if row and row["inserted"] == 1:
                await conn.execute("""
                  INSERT INTO events(topic, event_id, ts, source, payload)
                  VALUES($1,$2,$3,$4,$5::jsonb)
                  ON CONFLICT DO NOTHING;
                """, topic, event_id, ts, source, payload_json)
                await conn.execute("UPDATE stats SET unique_processed = unique_processed + 1 WHERE id=1;")
                return True
            else:
                await conn.execute("UPDATE stats SET duplicate_dropped = duplicate_dropped + 1 WHERE id=1;")
                return False

async def worker_loop(worker_id: int):
    r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    await ensure_group(r)
    pool = await get_pool()

    while True:
        resp = await r.xreadgroup(GROUP, f"{CONSUMER_NAME}-{worker_id}",
                                 streams={STREAM: ">"}, count=50, block=5000)
        if not resp:
            continue
        for _, messages in resp:
            for msg_id, fields in messages:
                ev = json.loads(fields["data"])
                await process_one(pool, ev)
                await r.xack(STREAM, GROUP, msg_id)  # ACK setelah transaksi commit

async def start_consumers(n: int):
    await asyncio.gather(*[worker_loop(i) for i in range(n)])
