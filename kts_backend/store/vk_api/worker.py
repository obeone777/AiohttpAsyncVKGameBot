import asyncio

from kts_backend.store import Store


class Worker:
    def __init__(self, store: Store, queue: asyncio.Queue):
        self.store = store
        self.queue = queue
        self.is_running = True

    async def start(self):
        while self.is_running or not self.queue.empty():
            update = await self.queue.get()
            await self.store.bots_manager.handle_updates(update)
            self.queue.task_done()

    async def stop(self):
        self.is_running = False
