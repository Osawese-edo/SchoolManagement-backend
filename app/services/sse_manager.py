import asyncio
import json

MAX_QUEUE_SIZE = 256

class SSEManager:
    def __init__(self):
        self._queues: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self.admin_exists: bool | None = None

    async def subscribe(self, queue: asyncio.Queue):
        async with self._lock:
            self._queues.append(queue)

    async def unsubscribe(self, queue: asyncio.Queue):
        async with self._lock:
            self._queues.remove(queue)

    async def emit(self, event: str, data: dict):
        payload = json.dumps(data)
        async with self._lock:
            for queue in self._queues:
                try:
                    await asyncio.wait_for(queue.put(f"event: {event}\ndata: {payload}\n\n"), timeout=1.0)
                except (asyncio.TimeoutError, asyncio.QueueFull):
                    pass

    async def update_admin_exists(self, value: bool):
        self.admin_exists = value
        await self.emit("setup-status-changed", {"admin_exists": value})


sse_manager = SSEManager()
