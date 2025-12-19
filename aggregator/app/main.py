import asyncio
import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
import redis.asyncio as redis

from .db import init_pool, get_pool
from .models import PublishRequest
from .consumer import start_consumers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")

START = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    log.info("lifespan startup: init db pool")
    await init_pool()

    log.info("lifespan startup: starting consumers")
    app.state.consumer_task = asyncio.create_task(start_consumers())

    yield  # aplikasi jalan di sini

    # ===== SHUTDOWN =====
    log.info("lifespan shutdown: stopping consumers")
    task = getattr(app.state, "consumer_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

@app.post("/publish")
async def publish(req: PublishRequest):
    r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    stream = os.getenv("REDIS_STREAM", "log-events")
    for ev in req.events:
        await r.xadd(stream, {"data": ev.model_dump_json()})
    return {"accepted": len(req.events)}

@app.get("/events")
async def events(topic: str | None = Query(default=None)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if topic:
            rows = await conn.fetch(
                "SELECT topic,event_id,ts,source,payload FROM events WHERE topic=$1 ORDER BY ts ASC;",
                topic
            )
        else:
            rows = await conn.fetch(
                "SELECT topic,event_id,ts,source,payload FROM events ORDER BY ts ASC;"
            )
    return [
        {
            "topic": r["topic"],
            "event_id": r["event_id"],
            "timestamp": r["ts"],
            "source": r["source"],
            "payload": r["payload"],
        }
        for r in rows
    ]

@app.get("/stats")
async def stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        s = await conn.fetchrow(
            "SELECT received, unique_processed, duplicate_dropped, started_at FROM stats WHERE id=1;"
        )
        topics = await conn.fetch(
            "SELECT topic, COUNT(*) AS n FROM events GROUP BY topic ORDER BY n DESC;"
        )

    return {
        "received": s["received"] if s else 0,
        "unique_processed": s["unique_processed"] if s else 0,
        "duplicate_dropped": s["duplicate_dropped"] if s else 0,
        "topics": [{"topic": t["topic"], "count": t["n"]} for t in topics],
        "uptime_seconds": int(time.time() - START),
    }
