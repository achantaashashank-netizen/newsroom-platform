import json
from collections.abc import AsyncGenerator
from datetime import datetime

import redis.asyncio as aioredis

from app.core.config import settings

_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
    return _pool


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_redis_pool())


async def emit_sse_event(
    redis: aioredis.Redis,
    run_id: str,
    event: str,
    data: dict,
) -> None:
    payload = json.dumps({
        "event": event,
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    })
    channel = f"run:{run_id}:logs"
    stream_key = f"stream:{run_id}"

    await redis.publish(channel, payload)
    await redis.xadd(
        stream_key,
        {"event": event, "payload": payload},
        maxlen=500,
    )
    # TTL 24h on stream for reconnect replay
    await redis.expire(stream_key, 86400)


async def get_redis_dep() -> AsyncGenerator[aioredis.Redis, None]:
    r = get_redis()
    try:
        yield r
    finally:
        await r.aclose()
