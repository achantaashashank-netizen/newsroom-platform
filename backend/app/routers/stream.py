import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.redis import get_redis_dep
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


async def sse_generator(run_id: str, redis: aioredis.Redis, request: Request):
    channel = f"run:{run_id}:logs"
    stream_key = f"stream:{run_id}"

    # Replay last 100 events from Redis Stream (reconnect resilience)
    try:
        history = await redis.xrange(stream_key, count=100)
        for _, fields in history:
            payload = fields.get("payload", "{}")
            event_type = fields.get("event", "message")
            yield f"event: {event_type}\ndata: {payload}\n\n"
    except Exception as exc:
        logger.warning("sse_replay_error", run_id=run_id, error=str(exc))

    # Subscribe to live events
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    heartbeat_interval = 15  # seconds
    last_heartbeat = asyncio.get_event_loop().time()

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            now = asyncio.get_event_loop().time()
            if now - last_heartbeat >= heartbeat_interval:
                yield "event: heartbeat\ndata: {}\n\n"
                last_heartbeat = now

            if message and message["type"] == "message":
                try:
                    raw = message["data"]
                    parsed = json.loads(raw)
                    event_type = parsed.get("event", "message")
                    yield f"event: {event_type}\ndata: {raw}\n\n"
                except Exception as parse_exc:
                    logger.warning("sse_parse_error", error=str(parse_exc))

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


@router.get("/{run_id}")
async def stream_run(
    run_id: str,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        sse_generator(run_id, redis, request),
        media_type="text/event-stream",
        headers=headers,
    )
