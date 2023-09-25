import typing
from logging import getLogger

from kts_backend.store.vk_api.datas import Update

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
                current_game = await self.app.store.vk_api.get_game_by_chatid(
                    update.object.message.peer_id
                )
                if current_game and current_game[0].status == True:
                    await self.app.store.vk_api.game_process(
                        game=current_game, update=update, chat_id=chat_id
                    )
                elif (
                    update.object.message.text
                    == "[club222330688|@club222330688] Узнай обо мне 🌍"
                    or update.object.message.text == "[club222330688|API KTS] Узнай обо мне 🌍"
                ):
                    await self.app.store.vk_api.send_message(
                        message=await self.app.store.vk_api.about_game(),
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                    )
                elif (
                    update.object.message.text
                    == "[club222330688|@club222330688] Старт игры 🚀"
                    or update.object.message.text == "[club222330688|API KTS] Старт игры 🚀"
                ):
                    await self.app.store.vk_api.start_game(
                        chat_id=update.object.message.peer_id
                    )
                else:
                    await self.app.store.vk_api.send_message(
                        message="Хотите начать игру?",
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                    )
