import asyncpg
import os

POOL: asyncpg.Pool | None = None

async def init_pool():
    global POOL
    POOL = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=10)

async def get_pool() -> asyncpg.Pool:
    assert POOL is not None
    return POOL
