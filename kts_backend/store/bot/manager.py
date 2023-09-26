import typing
from logging import getLogger

from kts_backend.store.bot.text_constants import preview_choice_list
from kts_backend.store.vk_api.datas import Update

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")

    async def handle_updates(self, update: Update):
        if update is not None:
            chat_id = await self.app.store.game.chat_id_converter(update.object.message.peer_id)
            current_game = await self.app.store.game.get_game(
                update.object.message.peer_id
            )
            if current_game and current_game.status == "start":
                await self.app.store.game.game_process(
                    game=current_game, update=update, chat_id=chat_id
                )
            elif (
                update.object.message.text in preview_choice_list[:2]
            ):
                await self.app.store.vk_api.send_message(
                    message=await self.app.store.game.about_game(),
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                )
            elif (
                update.object.message.text in preview_choice_list[2:]
            ):
                await self.app.store.game.start_game(
                    chat_id=update.object.message.peer_id
                )
            else:
                await self.app.store.vk_api.send_message(
                    message="Хотите начать игру?",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                )
