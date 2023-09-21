import asyncio
import typing
from logging import getLogger

from kts_backend.store.vk_api.datas import Message, Update

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, updates: list[Update]):
        if updates is not None:
            for update in updates:
                chat_id = update.object.message.peer_id - 2000000000
                await self.app.store.vk_api.send_message(
                    Message(
                        user_id=update.object.message.from_id,
                        text=update.object.message.text
                    ),
                    chat_id
                )





                # Просто тесты не обращать внимание!
                # await self.app.store.vk_api.get_conversation_members(chat_id=update.object.message.peer_id)
                # game = await self.app.store.vk_api.get_game_by_chatid(chat_id=update.object.message.peer_id)
                # if game is None: await self.app.store.vk_api.send_message(
                #     Message(
                #         user_id=update.object.message.from_id,
                #         text='Игра не найдена'
                #     ),
                #     chat_id
                # )
                # await self.app.store.vk_api.game_create(chat_id=update.object.message.peer_id)
                # game2 = await self.app.store.vk_api.get_game_by_chatid(chat_id=update.object.message.peer_id)
                # if game2:
                #     await self.app.store.vk_api.send_message(
                #         Message(
                #             user_id=update.object.message.from_id,
                #             text='Игра НАЙДЕНА!'
                #         ),
                #         chat_id
                #     )





