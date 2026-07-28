"""
Server-Sent Events (SSE) Router — Real-Time Live Push Stream.
Provides zero-latency notification streaming to React frontend clients.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Request, Query, HTTPException

logger = logging.getLogger("sse_events")
router = APIRouter(prefix="/events", tags=["Real-Time Stream"])

# Global event subscribers queue set
_subscribers: set = set()


def broadcast_event(event_type: str, data: dict):
    """
    Synchronous/Asynchronous helper to broadcast an event payload to all connected SSE clients.
    """
    message = {
        "event": event_type,
        "data": json.dumps(data)
    }
    for queue in list(_subscribers):
        try:
            queue.put_nowait(message)
        except Exception as e:
            logger.warning(f"[SSE] Error queuing event for subscriber: {e}")


def _validate_sse_token(token: str = Query(None)):
    """Validate JWT token passed as query parameter for SSE (EventSource doesn't support headers)."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        from app.auth.dependencies import decode_token
        payload = decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/stream", summary="Stream Real-Time System & Sync Events (SSE)")
async def stream_events(request: Request, token: str = Query(None)):
    """
    Server-Sent Events (SSE) stream endpoint.
    Clients connect via EventSource('/api/v1/events/stream?token=...') to receive real-time push events.
    """
    _validate_sse_token(token)
    from sse_starlette.sse import EventSourceResponse

    queue = asyncio.Queue()
    _subscribers.add(queue)
    logger.info(f"[SSE] Client connected. Active subscribers: {len(_subscribers)}")

    async def event_generator():
        try:
            yield {
                "event": "connected",
                "data": json.dumps({"status": "active", "message": "Real-time event stream established"})
            }
            
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield {
                        "event": "ping",
                        "data": json.dumps({"type": "keep-alive"})
                    }
        finally:
            _subscribers.remove(queue)
            logger.info(f"[SSE] Client disconnected. Remaining subscribers: {len(_subscribers)}")

    return EventSourceResponse(event_generator())
