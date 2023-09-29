import typing

from kts_backend.store.database.database import Database


if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class Store:
    def __init__(self, app: "Application", *args, **kwargs):
        from kts_backend.store.admin.accessor import AdminAccessor
        from kts_backend.store.bot.manager import BotManager
        from kts_backend.store.game.accessor import GameAccessor
        from kts_backend.store.vk_api.accessor import VkApiAccessor
        from kts_backend.store.users.accessor import UserAccessor
        from kts_backend.store.question.accessor import QuestionAccessor

        self.admins = AdminAccessor(app)
        self.bots_manager = BotManager(app)
        self.game = GameAccessor(app)
        self.user = UserAccessor(app)
        self.vk_api = VkApiAccessor(app)
        self.question = QuestionAccessor(app)

def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)

