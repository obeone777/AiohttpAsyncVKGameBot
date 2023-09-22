import json
import random
import typing
from typing import Optional

from aiohttp import TCPConnector
from aiohttp.client import ClientSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import joinedload

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.base.models import GameUserAssociation
from kts_backend.game.models import (
    GameModel,
    Game,
    GameScore,
    QuestionAnswerModel,
    QuestionAnswer,
)
from kts_backend.store.vk_api.datas import (
    # Message,
    Update,
    UpdateObject,
    UpdateMessage,
)
from kts_backend.store.vk_api.poller import Poller
from kts_backend.users.models import UserModel, User

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

    async def send_message(self, message: str, chat_id: int, keyboard) -> None:
        async with self.session.get(
            self._build_query(
                VK_API_URL,
                "messages.send",
                params={
                    "random_id": random.randint(1, 2**32),
                    "chat_id": chat_id,
                    "message": message,
                    "access_token": self.app.config.bot.token,
                    "keyboard": keyboard,
                },
            )
        ) as resp:
            data = await resp.json()
            self.logger.info(data)

    async def get_conversation_members(self, chat_id: int) -> list[User]:
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
            users = data["response"]["profiles"]
            self.logger.info(users)
            return [
                User(
                    vk_id=user["id"],
                    name=user["first_name"],
                    last_name=user["last_name"],
                )
                for user in users
            ]

    async def get_game_by_chatid(self, chat_id: int) -> list[Game, User]:
        game_query = (
            select(GameModel)
            .options(
                joinedload(GameModel.players).joinedload(GameModel.question)
            )
            .where(GameModel.chat_id == chat_id)
            .order_by(desc(GameModel.created_at))
            .limit(1)
        )
        response = await self.app.database.orm_select(query=game_query)
        game = response.scalar()
        self.logger.info(game)
        if not game:
            return None
        game_user_query = select(GameUserAssociation).where(
            GameUserAssociation.game_id == game.id
        )
        game_user_response = await self.app.database.orm_select(
            query=game_user_query
        )
        game_users = game_user_response.scalars().all()
        self.logger.info(game_users)
        players = [
            GameScore(
                points=game_user.points,
                user_id=game_user.user_vk_id,
                game_id=game.id,
                user_is_active=game_user.user_is_active,
                user_turn=game_user.user_turn,
            )
            for game_user in game_users
        ]

        return [
            Game(
                id=game.id,
                created_at=game.created_at,
                chat_id=game.chat_id,
                status=game.status,
                players=players,
                question=game.question,
            ),
            [
                User(vk_id=user.vk_id, name=user.name, last_name=user.last_name)
                for user in game.players
            ],
        ]

    async def get_user_by_vkid(self, vkid: int) -> User:
        query = select(UserModel).where(UserModel.vk_id == vkid)
        user = await self.app.database.orm_select(query)
        user = user.scalar()
        self.logger.info(user)
        return User(vk_id=vkid, name=user.name, last_name=user.last_name)

    async def get_questuion(self):
        query = select(QuestionAnswerModel).order_by(func.random()).limit(1)
        result = await self.app.database.orm_select(query)
        result = result.scalar()
        return QuestionAnswer(
            id=result.id,
            question_text=result.question_text,
            answer_text=result.answer_text,
        )

    async def game_create(self, chat_id: int) -> list[Game, User]:
        users = await self.get_conversation_members(chat_id=chat_id)
        query = select(UserModel.vk_id).where(
            UserModel.vk_id.in_([user.vk_id for user in users])
        )
        result = await self.app.database.orm_select(query)
        existing_users_vk_ids = result.scalars().all()
        new_users = [
            UserModel(
                vk_id=user.vk_id, name=user.name, last_name=user.last_name
            )
            for user in users
            if user.vk_id not in existing_users_vk_ids
        ]
        new_game = GameModel(chat_id=chat_id)
        await self.app.database.orm_add(new_users + [new_game])
        game_id = new_game.id
        associations = [
            GameUserAssociation(game_id=game_id, user_vk_id=user.vk_id)
            for user in users
        ]
        await self.app.database.orm_add(associations)
        game_scores = [
            GameScore(
                user_id=association.user_vk_id,
                game_id=game_id,
            )
            for association in associations
        ]
        game_dataclass = Game(
            id=game_id,
            created_at=new_game.created_at,
            chat_id=chat_id,
            players=game_scores,
            question=new_game.question,
        )

        return [game_dataclass, new_users]

    async def one_button_creater(self, text: str, color: str) -> dict:
        return {
            "action": {
                "type": "text",
                "payload": '{"button": "' + "1" + '"}',
                "label": text,
            },
            "color": color,
        }

    async def get_preview_keyboard(self) -> str:
        keyboard = {
            "inline": True,
            "buttons": [
                [
                    await self.one_button_creater(
                        "Узнай обо мне 🌍", "positive"
                    ),
                    await self.one_button_creater("Старт игры 🚀", "positive"),
                ]
            ],
        }
        keyboard = json.dumps(keyboard, ensure_ascii=False).encode("utf-8")
        return str(keyboard.decode("utf-8"))

    async def get_default_keyboard(self) -> str:
        keyboard = {
            "inline": True,
            "buttons": [
                [await self.one_button_creater("Бот отвечает", "positive")]
            ],
        }
        keyboard = json.dumps(keyboard, ensure_ascii=False).encode("utf-8")
        return str(keyboard.decode("utf-8"))

    async def get_game_keyboard(self) -> str:
        keyboard = {
            "inline": True,
            "buttons": [
                [
                    await self.one_button_creater(
                        "Выбрать букву 💬", "positive"
                    ),
                    await self.one_button_creater(
                        "Назвать слово 🗣", "positive"
                    ),
                ]
            ],
        }
        keyboard = json.dumps(keyboard, ensure_ascii=False).encode("utf-8")
        return str(keyboard.decode("utf-8"))

    async def about_game(self):
        return """Привет, я бот "ПолеЧудес". Правила игры просты:
                При старте игры в чат присылается загадка и тебе необходимо либо назвать букву, либо попытаться сразу угадать слово.
                При верно угаданной букве, откроются все выбранные буквы, которые присутствуют в слове и ты получишь +1 очко.
                При неудачном варианте, ход переходит к следующему игроку.
                Однако если ты назовешь неверное слово, ты выбываешь. Если же названо верное слово, ты становишься победителем"""

    async def start_game(self, chat_id: int) -> list[Game, User]:
        game = await self.game_create(chat_id)
        user = game[1][0]
        question = await self.get_questuion()
        await self.send_message(
            message=f"Внимание загадка! {question.question_text}?",
            chat_id=chat_id - 2000000000,
            keyboard=await self.get_default_keyboard(),
        )
        await self.send_message(
            message=f"{user.name} {user.last_name} твой ход! Выбери букву или назови слово.",
            chat_id=chat_id - 2000000000,
            keyboard=await self.get_game_keyboard(),
        )
        return game

    # async def choosing_letter(self, user, chat_id, update: Update, game_lst: list[Game, User]):
    #     if (
    #         len(update.object.message.text) != 1
    #         or update.object.message.text not in game_lst[0].question
    #     ):
    #         await self.send_message(
    #             message=f"{user.name}, {user.last_name} такой буквы нет в слове!",
    #             chat_id=chat_id,
    #             keyboard=self.get_default_keyboard(),
    #         )
    #         user = ...
    #         return user
    #     await self.send_message(
    #         message=f"{user.name}, {user.last_name} правильно, буква угадана! + 1 балл!",
    #         chat_id=chat_id,
    #         keyboard=self.get_default_keyboard(),
    #     )
    #     return user
