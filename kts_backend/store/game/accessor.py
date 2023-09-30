import asyncio
import random
from typing import Union, Optional

from sqlalchemy import func, select, and_, case, update, desc
from sqlalchemy.orm import joinedload

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.base.models import GameScore
from kts_backend.game.models import Game
from kts_backend.question.models import QuestionAnswer
from kts_backend.store.game.text_constants import (
    text_about_game,
    choice_list,
    no_questions,
    next_turn,
    id_constant,
)
from kts_backend.store.vk_api.datas import Update
from kts_backend.users.models import User

questions = {}


class GameAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.locks = {}

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

    async def game_process(
        self, game: Game, update: Update, chat_id: int
    ) -> None:
        if chat_id not in self.locks:
            self.locks[chat_id] = asyncio.Lock()
        async with self.locks[chat_id]:
            new_message = update.object.message.text.split("] ")[-1]
            if new_message == choice_list[2]:
                await self.no_players_left(game, chat_id)
                await self.last_action_change(game, new_message)
                return None
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
                    if new_message != game.last_action:
                        await self.last_action_change(game, new_message)
                    await self.app.store.vk_api.send_message(
                        message=f"{user.name} напишите букву/слово согласно раннее выбранному варианту!",
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_default_keyboard(),
                    )
                elif not game.last_action:
                    return None
                else:
                    if game.last_action == choice_list[0]:
                        await self.choose_letter(
                            game, new_message, user, chat_id, game.players
                        )
                    elif game.last_action == choice_list[1]:
                        await self.choose_word(
                            game, new_message, user, chat_id, game.players
                        )

    async def choose_letter(
        self,
        game: Game,
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
            new_message_lower = new_message.lower()
            game.question.answer_text_lower = game.question.answer_text.lower()
            if new_message_lower in game.question.answer_text_lower:
                revealed_letters = game.letters_revealed + new_message_lower
                display_word = "".join(
                    [
                        letter if letter.lower() in revealed_letters else "-"
                        for letter in game.question.answer_text
                    ]
                )
                if len(set(revealed_letters)) == len(
                    set(game.question.answer_text)
                ):
                    await self.plus_points("word", game, user)
                    game = await self.get_game(chat_id + id_constant)
                    await self.game_over(user, chat_id, game)
                else:
                    counter = game.question.answer_text_lower.count(
                        new_message_lower
                    )
                    await self.plus_points("letter", game, user, counter)
                    await self.app.store.vk_api.send_message(
                        message=f"{display_word}. Снова выберите букву или слово",
                        chat_id=chat_id,
                        keyboard=await self.app.store.vk_api.get_game_keyboard(),
                    )
                await self.app.database.orm_update(
                    Game,
                    {"id": game.id},
                    {
                        "last_action": new_message,
                        "letters_revealed": revealed_letters,
                    },
                )

            else:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} такой буквы нет!",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
                await self.choose_next_user_for_answer(
                    game, user, chat_id, game_users
                )
                await self.last_action_change(game, new_message)

    async def choose_word(
        self,
        game: Game,
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
            if new_message.lower() == game.question.answer_text.lower():
                await self.plus_points("word", game, user)
                game = await self.get_game(chat_id + id_constant)
                await self.game_over(user, chat_id, game)
            else:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} {user.last_name} неверно, вы исключены из игры!",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
                counter = sum(
                    map(lambda player: player.user_is_active, game.scores)
                )
                if counter == 1:
                    await self.no_players_left(game, chat_id)
                    return None
                await self.app.database.orm_update(
                    GameScore,
                    {
                        "user_vk_id": user.vk_id,
                        "game_id": game.id,
                    },
                    {"user_is_active": False},
                )
                await self.choose_next_user_for_answer(
                    game, user, chat_id, game_users
                )
            await self.last_action_change(game, new_message)

    async def choose_next_user_for_answer(
        self,
        game: Game,
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
                "id": game.id,
            },
            {"turn_user_id": random_user.vk_id},
        )
        await self.app.store.vk_api.send_message(
            message=f"{random_user.name} {random_user.last_name} {next_turn}",
            chat_id=chat_id,
            keyboard=await self.app.store.vk_api.get_game_keyboard(),
        )

    async def game_over(self, user: User, chat_id: int, game: Game) -> None:
        await self.app.store.vk_api.send_message(
            message=f"{user.name} {user.last_name} поздравляю вы выиграли! {game.question.answer_text} верный ответ! "
            f"{await self.get_game_leaderboard(game)}",
            chat_id=chat_id,
            keyboard=await self.app.store.vk_api.get_preview_keyboard(),
        )
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"status": "finish"},
        )
        data = {player.user_vk_id: player.points for player in game.scores}
        self.logger.info(f"Я ТУТ Я ТУТ! {data}")
        whens = [
            (User.vk_id == id, User.total_points + points)
            for id, points in data.items()
        ]
        query = (
            update(User)
            .values(total_points=case(*whens, else_=User.total_points))
            .where(User.vk_id.in_(data.keys()))
        )
        await self.app.database.orm_list_update(query)

    async def get_game_leaderboard(self, game: Game) -> str:
        leaderboard = {
            next(
                f"{player.name} {player.last_name}"
                for player in game.players
                if player.vk_id == gamescore.user_vk_id
            ): gamescore.points
            for gamescore in game.scores
        }
        output = ", ".join(
            [f"{key}: {value}" for key, value in leaderboard.items()]
        )
        return f"Таблица лидеров игры номер {game.id} - {output}"

    async def get_world_leaderboard(self, chat_id: int) -> str:
        users = await self.app.store.vk_api.get_conversation_members(chat_id)
        users_id = [user.vk_id for user in users]
        query = (
            select(User)
            .where(User.vk_id.in_(users_id))
            .order_by(desc(User.total_points))
        )
        chat_users = await self.app.database.orm_select(query)
        chat_users = chat_users.scalars().all()
        if not chat_users:
            return "Ни один из пользователей чата еще не сыграл игру!"
        leaderboard = {
            f"{user.name} {user.last_name}": user.total_points
            for user in chat_users
        }
        output = ", ".join(
            [f"{key}: {value}" for key, value in leaderboard.items()]
        )
        return f"Общее количество баллов за все игры {output}"

    @staticmethod
    async def chat_id_converter(chat_id: int) -> int:
        return chat_id - id_constant

    async def plus_points(
        self, type: str, game: Game, user: User, counter: int = 1
    ) -> None:
        query = select(GameScore.points).where(
            and_(
                GameScore.game_id == game.id, GameScore.user_vk_id == user.vk_id
            )
        )
        result = await self.app.database.orm_select(query)
        result = result.scalar()
        if type == "letter":
            new_points = result + counter
        else:
            new_points = result + 10
        await self.app.database.orm_update(
            GameScore,
            {"game_id": game.id, "user_vk_id": user.vk_id},
            {"points": new_points},
        )

    async def last_action_change(self, game: Game, new_message: str) -> None:
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"last_action": new_message},
        )

    async def get_leaderboard_api(self) -> list:
        query = select(User.name, User.last_name, User.total_points).order_by(
            desc(User.total_points)
        )
        result = await self.app.database.orm_select(query)
        users = []
        for row in result:
            user = {
                "name": row.name,
                "last_name": row.last_name,
                "total_points": row.total_points,
            }
            users.append(user)
        return users

    async def no_players_left(self, game: Game, chat_id: int) -> None:
        await self.app.store.vk_api.send_message(
            message=f"Игра окончена! "
            f"{await self.get_game_leaderboard(game)}",
            chat_id=chat_id,
            keyboard=await self.app.store.vk_api.get_preview_keyboard(),
        )
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"status": "finish"},
        )
