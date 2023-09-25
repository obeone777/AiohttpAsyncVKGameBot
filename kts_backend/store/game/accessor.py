import random
from typing import Union, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.base.models import GameScore
from kts_backend.game.models import Game, QuestionAnswer
from kts_backend.store.game.text_constants import (
    text_about_game,
    choice_list,
    no_questions,
    next_turn,
)
from kts_backend.store.vk_api.datas import Update
from kts_backend.users.models import User

games = {}
questions = {}
answer = {}


class GameAccessor(BaseAccessor):
    async def get_game(self, chat_id: int) -> Union[Game, None]:
        game_query = (
            select(Game)
            .options(
                joinedload(Game.question),
                joinedload(Game.scores),
                joinedload(Game.players).joinedload(User.games),
            )
            .filter(Game.chat_id == chat_id)
            .order_by(Game.created_at.desc())
            .limit(1)
        )
        response = await self.app.database.orm_select(query=game_query)
        game = response.scalar()
        if not game:
            return None
        return game

    async def get_question(self, chat_id) -> Union[QuestionAnswer, None]:
        if chat_id in questions:
            query = (
                select(QuestionAnswer)
                .order_by(func.random())
                .where(QuestionAnswer.question_text.notin_(questions[chat_id]))
            )
        else:
            query = select(QuestionAnswer).order_by(func.random())

        result = await self.app.database.orm_select(query)

        question = result.scalar()
        if not question:
            await self.app.store.vk_api.send_message(
                message=no_questions,
                chat_id=chat_id,
                keyboard=await self.app.store.vk_api.get_default_keyboard(),
            )
            return None

        questions.setdefault(chat_id, []).append(question.question_text)
        return question

    async def game_create(self, chat_id: int) -> Optional[bool]:
        users = await self.app.store.vk_api.get_conversation_members(
            chat_id=chat_id
        )

        result_query = await self.app.database.orm_select(
            select(User.vk_id).where(
                User.vk_id.in_([user.vk_id for user in users])
            )
        )

        existing_users_vk_ids = [user for user in result_query.scalars().all()]

        new_users = [
            User(vk_id=user.vk_id, name=user.name, last_name=user.last_name)
            for user in users
            if user.vk_id not in existing_users_vk_ids
        ]

        question = await self.get_question(
            await self.chat_id_converter(chat_id)
        )
        if not question:
            return True

        new_game = Game(chat_id=chat_id, question=question)
        await self.app.database.orm_add(new_users + [new_game])

        associations = [
            GameScore(game_id=new_game.id, user_vk_id=user.vk_id)
            for user in users
        ]
        await self.app.database.orm_add(associations)

    @staticmethod
    async def about_game() -> str:
        return text_about_game

    async def start_game(self, chat_id: int) -> Union[Game, None]:
        creating = await self.game_create(chat_id)
        if creating:
            return None
        game = await self.get_game(chat_id)
        user = random.choice(game.players)
        if game is None:
            return None
        await self.app.store.vk_api.send_message(
            message=f"Внимание, загадка! {game.question.question_text}?",
            chat_id=await self.chat_id_converter(chat_id),
            keyboard=await self.app.store.vk_api.get_default_keyboard(),
        )
        await self.app.store.vk_api.send_message(
            message=f"{user.name} {user.last_name} {next_turn}",
            chat_id=await self.chat_id_converter(chat_id),
            keyboard=await self.app.store.vk_api.get_game_keyboard(),
        )
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"turn_user_id": user.vk_id},
        )
        games[game.id] = "Старт"
        return game

    async def game_process(
        self, game: Game, update: Update, chat_id: int
    ) -> None:
        new_message = update.object.message.text
        user = next(
            (
                u
                for u in game.players
                if u.vk_id == update.object.message.from_id
            ),
            None,
        )
        if user:
            player = next(
                (
                    player
                    for player in game.scores
                    if player.user_vk_id == user.vk_id
                ),
                None,
            )
            if not (
                player
                and player.user_is_active
                and game.turn_user_id == player.user_vk_id
            ):
                return None
            elif new_message in choice_list:
                games[game.id] = new_message
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} напишите букву/слово согласно раннее выбранному варианту!",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
            elif games[game.id] == "Старт":
                return None
            else:
                if (
                    games[game.id] == choice_list[0]
                    or games[game.id] == choice_list[2]
                ):
                    await self.choose_letter(
                        game, new_message, user, chat_id, game.players
                    )
                elif (
                    games[game.id] == choice_list[1]
                    or games[game.id] == choice_list[3]
                ):
                    await self.choose_word(
                        game, new_message, user, chat_id, game.players
                    )

    async def choose_letter(
        self,
        current_game: Game,
        new_message: str,
        user: User,
        chat_id: int,
        game_users: list[User],
    ) -> None:
        if len(new_message) != 1:
            await self.app.store.vk_api.send_message(
                message=f"{user.name} {user.last_name} выберите 1 букву!",
                chat_id=chat_id,
                keyboard=await self.app.store.vk_api.get_default_keyboard(),
            )
        else:
            revealed_indexes = answer.get(current_game.id, [])
            if new_message.lower() in current_game.question.answer_text.lower():
                indexes = [
                    index
                    for index, value in enumerate(
                        current_game.question.answer_text.lower()
                    )
                    if value == new_message.lower()
                ]
                revealed_indexes.extend(indexes)
                answer[current_game.id] = revealed_indexes
                display_word = "".join(
                    [
                        current_game.question.answer_text[i]
                        if i in revealed_indexes
                        else "-"
                        for i in range(len(current_game.question.answer_text))
                    ]
                )
                if len(set(revealed_indexes)) == len(
                    current_game.question.answer_text
                ):
                    await self.game_over(user, chat_id, current_game)
                else:
                    await self.app.store.vk_api.send_message(
                        message=f"{display_word}. Снова выберите букву или слово",
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_game_keyboard(),
                    )
                    games[current_game.id] = new_message
            else:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} такой буквы нет!",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
                await self.choose_next_user_for_answer(
                    current_game, user, chat_id, game_users
                )
                games[current_game.id] = new_message

    async def choose_word(
        self,
        current_game: Game,
        new_message: str,
        user: User,
        chat_id: int,
        game_users: list[User],
    ) -> None:
        if len(new_message) == 1:
            await self.app.store.vk_api.send_message(
                message=f"{user.name} {user.last_name} назовите слово!",
                chat_id=chat_id,
                keyboard=await self.app.store.vk_api.get_default_keyboard(),
            )
        else:
            if new_message.lower() == current_game.question.answer_text.lower():
                await self.game_over(user, chat_id, current_game)
            else:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} {user.last_name} неверно, вы исключены из игры!",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
                await self.app.database.orm_update(
                    GameScore,
                    {
                        "user_vk_id": user.vk_id,
                        "game_id": current_game.id,
                    },
                    {"user_is_active": False},
                )
                await self.choose_next_user_for_answer(
                    current_game, user, chat_id, game_users
                )

    async def choose_next_user_for_answer(
        self,
        current_game: Game,
        user: User,
        chat_id: int,
        game_users: list[User],
    ) -> None:
        random_user = random.choice(game_users)
        while user == random_user:
            random_user = random.choice(game_users)
        await self.app.database.orm_update(
            Game,
            {
                "id": current_game.id,
            },
            {"turn_user_id": random_user.vk_id},
        )
        await self.app.store.vk_api.send_message(
            message=f"{random_user.name} {random_user.last_name} {next_turn}",
            chat_id=chat_id,
            keyboard=await self.app.store.vk_api.get_game_keyboard(),
        )

    async def game_over(
        self, user: User, chat_id: int, current_game: Game
    ) -> None:
        await self.app.store.vk_api.send_message(
            message=f"{user.name} {user.last_name} поздравляю вы выиграли! {current_game.question.answer_text} верный ответ!",
            chat_id=chat_id,
            keyboard=await self.app.store.vk_api.get_preview_keyboard(),
        )
        await self.app.database.orm_update(
            Game,
            {"id": current_game.id},
            {"status": "finish"},
        )

    async def chat_id_converter(self, chat_id: int) -> int:
        return chat_id - 2000000000
