import random
import typing
from typing import Optional

from aiohttp import TCPConnector
from aiohttp.client import ClientSession

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.store.vk_api.datas import (
    Message,
    Update,
    UpdateObject,
    UpdateMessage,
)
from kts_backend.store.vk_api.poller import Poller

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application

VK_API_URL = "https://api.vk.com/method/"


class VkApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.session: Optional[ClientSession] = None
        self.key: Optional[str] = None
        self.server: Optional[str] = None
        self.poller: Optional[Poller] = None
        self.ts: Optional[int] = None

    async def connect(self, app: "Application"):
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False))
        try:
            await self._get_long_poll_service()
        except Exception as e:
            self.logger.error("Exception", exc_info=e)
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        await self.poller.start()

    async def disconnect(self, app: "Application"):
        if self.session:
            await self.session.close()
        if self.poller:
            await self.poller.stop()

    @staticmethod
    def _build_query(host: str, method: str, params: dict) -> str:
        url = host + method + "?"
        if "v" not in params:
            params["v"] = "5.131"
        url += "&".join([f"{k}={v}" for k, v in params.items()])
        return url

    async def _get_long_poll_service(self):
        """Запрос сервера для Long Polling, получение его параметров"""
        async with self.session.get(
            self._build_query(
                host=VK_API_URL,
                method="groups.getLongPollServer",
                params={
                    "group_id": self.app.config.bot.group_id,
                    "access_token": self.app.config.bot.token,
                },
            )
        ) as resp:
            data = (await resp.json())["response"]
            self.logger.info(data)
            self.server = data["server"]
            self.key = data["key"]
            self.ts = data["ts"]
            self.logger.info(self.server)

    async def poll(self):
        """Отправление Long Poll запроса и получение списка класса Update"""
        async with self.session.get(
            self._build_query(
                host=self.server,
                method="",
                params={
                    "act": "a_check",
                    "key": self.key,
                    "ts": self.ts,
                    "wait": 30,
                },
            )
        ) as resp:
            data = await resp.json()
            self.logger.info(data)
            self.ts = data["ts"]
            raw_updates = data.get("updates")
            update_list = [
                Update(
                    type=update["type"],
                    object=UpdateObject(
                        message=UpdateMessage(
                            from_id=update["object"]["message"]["from_id"],
                            text=update["object"]["message"]["text"],
                            id=update["object"]["message"]["id"],
                            peer_id=update["object"]["message"]["peer_id"],
                        )
                    ),
                )
                for update in raw_updates
            ]
            await self.app.store.bots_manager.handle_updates(update_list)

    async def send_message(self, message: Message, chat_id: int) -> None:
        async with self.session.get(
            self._build_query(
                VK_API_URL,
                "messages.send",
                params={
                    "random_id": random.randint(1, 2**32),
                    "chat_id": chat_id,
                    "message": message.text,
                    "access_token": self.app.config.bot.token,
                },
            )
        ) as resp:
            data = await resp.json()
            self.logger.info(data)

    async def get_conversation_members(self, chat_id: int) -> list:
        async with self.session.get(
            self._build_query(
                VK_API_URL,
                "messages.getConversationMembers",
                params={
                    "peer_id": chat_id,
                    "fields": "id",
                    "access_token": self.app.config.bot.token,
                },
            )
        ) as resp:
            data = await resp.json()
            self.logger.info(data["response"]["profiles"])
            return data["response"]["profiles"]

    async def game_create(self, players: list, chat_id: int) -> None:
        pass
