import asyncio
from asyncio import Task
from typing import Optional

from kts_backend.store import Store


class Poller:
    def __init__(self, store: Store, queue: asyncio.Queue):
        self.store = store
        self.queue = queue
        self.is_running = False
        self.poll_task: Optional[Task] = None

    async def start(self):
        self.is_running = True
        self.poll_task = asyncio.create_task(self.poll())

    async def stop(self):
        self.is_running = False
        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

    async def poll(self):
        while self.is_running:
            updates = await self.store.vk_api.poll()
            for update in updates:
                await self.queue.put(update)
