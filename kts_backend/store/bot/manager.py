import typing
from logging import getLogger

from aiolimiter import AsyncLimiter

from kts_backend.store.bot.text_constants import (
    INFO_CMD,
    LEADERBOARD_CMD,
    START_CMD,
    next_turn,
)
from kts_backend.store.game.utils import about_game, chat_id_converter
from kts_backend.store.vk_api.datas import Update

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")
        self.user_limiters = {}

    async def handle_updates(self, update: typing.Optional[Update]):
        if update is not None:
            user_id = update.object.message.from_id
            if user_id not in self.user_limiters:
                self.user_limiters[user_id] = AsyncLimiter(
                    max_rate=3, time_period=1
                )
            limiter = self.user_limiters[user_id]
            async with limiter:
                new_message = update.object.message.text.split("] ")[-1]
                chat_id = chat_id_converter(update.object.message.peer_id)
                current_game = await self.app.store.game.get_game(
                    update.object.message.peer_id
                )
                if current_game and current_game.status_last_action != "finish":
                    await self.app.store.game.game_process(
                        game=current_game, message=new_message, user_id=user_id
                    )
                elif new_message == INFO_CMD:
                    await self.app.store.vk_api.send_message(
                        message=about_game(),
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                    )
                elif new_message == START_CMD:
                    game_user = await self.app.store.game.start_game(
                        chat_id=update.object.message.peer_id
                    )
                    if game_user:
                        game = game_user[0]
                        user = game_user[1]
                        await self.app.store.vk_api.send_message(
                            message=f"Внимание, загадка! {game.question.question}?",
                            chat_id=chat_id,
                            keyboard=await self.app.store.vk_api.get_default_keyboard(),
                        )
                        await self.app.store.vk_api.send_message(
                            message=f"{user.name} {user.last_name} {next_turn}",
                            chat_id=chat_id,
                            keyboard=await self.app.store.vk_api.get_game_keyboard(),
                        )
                elif new_message == LEADERBOARD_CMD:
                    await self.app.store.vk_api.send_message(
                        message=await self.app.store.game.get_world_leaderboard(
                            update.object.message.peer_id
                        ),
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                    )
                else:
                    await self.app.store.vk_api.send_message(
                        message="Хотите начать игру?",
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_preview_keyboard(),
                    )
