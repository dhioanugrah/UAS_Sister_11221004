import asyncio
import json
import os
import logging
from typing import Any, Dict
from datetime import datetime, timezone


import redis.asyncio as redis
import asyncpg

from .db import get_pool

log = logging.getLogger(__name__)

CONSUMER_WORKERS = int(os.getenv("CONSUMER_WORKERS", "4"))
STREAM = os.getenv("REDIS_STREAM", "log-events")
GROUP = os.getenv("REDIS_GROUP", "agg-group")
CONSUMER_PREFIX = os.getenv("REDIS_CONSUMER_PREFIX", "worker")
BLOCK_MS = int(os.getenv("REDIS_BLOCK_MS", "2000"))
BATCH = int(os.getenv("REDIS_BATCH", "50"))

REDIS_URL = os.environ["REDIS_URL"]


def _parse_event(data_str: str) -> Dict[str, Any]:
    return json.loads(data_str)


async def _ensure_group(r: redis.Redis):
    try:
        await r.xgroup_create(name=STREAM, groupname=GROUP, id="0", mkstream=True)
        log.info("Created consumer group=%s stream=%s", GROUP, STREAM)
    except Exception as e:
        # group sudah ada -> BUSYGROUP
        if "BUSYGROUP" in str(e):
            return
        raise

def parse_iso_ts(ts: str) -> datetime:
    # contoh input: "2025-12-19T17:43:36.427813Z"
    # Python: Z tidak langsung diparse -> ganti jadi +00:00
    if ts.endswith("Z"):
        ts = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


async def _process_one(conn: asyncpg.Connection, ev: Dict[str, Any]) -> str:
    topic = ev["topic"]
    event_id = ev["event_id"]
    ts = parse_iso_ts(ev["timestamp"])
    source = ev.get("source", "")
    payload = ev.get("payload", {})

    inserted = await conn.fetchval(
        """
        INSERT INTO processed_events(topic, event_id, processed_at)
        VALUES($1, $2, NOW())
        ON CONFLICT (topic, event_id) DO NOTHING
        RETURNING 1;
        """,
        topic, event_id
    )


    if inserted:
        await conn.execute(
            """
            INSERT INTO events(topic, event_id, ts, source, payload)
            VALUES($1, $2, $3, $4, $5);
            """,
            topic, event_id, ts, source, json.dumps(payload)
        )
        await conn.execute(
            """
            UPDATE stats
            SET received = received + 1,
                unique_processed = unique_processed + 1
            WHERE id = 1;
            """
        )
        return "unique"
    else:
        await conn.execute(
            """
            UPDATE stats
            SET received = received + 1,
                duplicate_dropped = duplicate_dropped + 1
            WHERE id = 1;
            """
        )
        return "dup"


async def consumer_loop(worker_id: int):
    r = redis.from_url(REDIS_URL, decode_responses=True)
    await _ensure_group(r)

    consumer_name = f"{CONSUMER_PREFIX}-{worker_id}"
    pool = await get_pool()

    log.info("Consumer started: %s (group=%s stream=%s)", consumer_name, GROUP, STREAM)

    while True:
        try:
            resp = await r.xreadgroup(
                groupname=GROUP,
                consumername=consumer_name,
                streams={STREAM: ">"},
                count=BATCH,
                block=BLOCK_MS
            )

            if not resp:
                continue

            _, messages = resp[0]
            for msg_id, fields in messages:
                data_str = fields.get("data")
                if not data_str:
                    await r.xack(STREAM, GROUP, msg_id)
                    continue

                ev = _parse_event(data_str)

                async with pool.acquire() as conn:
                    async with conn.transaction():
                        outcome = await _process_one(conn, ev)

                await r.xack(STREAM, GROUP, msg_id)

                if outcome == "unique":
                    log.info("processed unique %s/%s", ev["topic"], ev["event_id"])
                else:
                    log.info("dropped duplicate %s/%s", ev["topic"], ev["event_id"])

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("consumer error: %s", e)
            await asyncio.sleep(0.5)


async def start_consumers():
    workers = [asyncio.create_task(consumer_loop(i)) for i in range(CONSUMER_WORKERS)]
    log.info("Consumers started: %s", CONSUMER_WORKERS)
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers:
            w.cancel()
        raise
