import asyncio
import random
from typing import Optional, Union

from sqlalchemy import case, desc, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.base.models import GameScore
from kts_backend.game.models import Game
from kts_backend.question.models import Question
from kts_backend.store.bot.text_constants import next_turn
from kts_backend.store.game.text_constants import (action_for_decision,
                                                   choice_list, choose_again,
                                                   choose_one_letter,
                                                   chose_word, failed_letter,
                                                   game_leaderboard, game_over,
                                                   id_constant, letter_exist,
                                                   no_questions, noone_played,
                                                   total_points, user_kicked)
from kts_backend.store.game.utils import chat_id_converter
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

    async def get_question(self, chat_id) -> Union[Question, None]:
        if chat_id in questions:
            query = (
                select(Question)
                .order_by(func.random())
                .where(Question.question.notin_(questions[chat_id]))
            )
        else:
            query = select(Question).order_by(func.random())

        result = await self.app.database.orm_select(query)

        question = result.scalar()
        if not question:
            await self.app.store.vk_api.send_message(
                message=no_questions,
                chat_id=chat_id,
                keyboard=await self.app.store.vk_api.get_default_keyboard(),
            )
            return None

        questions.setdefault(chat_id, []).append(question.question)
        return question

    async def game_create(self, chat_id: int) -> Optional[bool]:
        users = await self.app.store.vk_api.get_conversation_members(
            chat_id=chat_id
        )
        new_user_values = [
            {
                "vk_id": user.vk_id,
                "name": user.name,
                "last_name": user.last_name,
                "total_points": 0,
            }
            for user in users
        ]
        stmt = (
            insert(User)
            .values(new_user_values)
            .on_conflict_do_nothing(index_elements=["vk_id"])
        )
        await self.app.database.orm_list_update(stmt)
        question = await self.get_question(chat_id_converter(chat_id))
        if not question:
            return True
        new_game = Game(chat_id=chat_id, question=question)
        await self.app.database.orm_add(new_game)
        associations = [
            GameScore(game_id=new_game.id, user_vk_id=user.vk_id)
            for user in users
        ]
        await self.app.database.orm_add(associations)

    async def start_game(self, chat_id: int) -> Union[tuple[Game, User], None]:
        creating = await self.game_create(chat_id)
        if creating:
            return None
        game = await self.get_game(chat_id)
        user = random.choice(game.players)
        if game is None:
            return None
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"turn_user_id": user.vk_id},
        )
        return (game, user)

    async def game_process(
        self, game: Game, message: str, user_id: int
    ) -> None:
        chat_id = chat_id_converter(game.chat_id)
        if chat_id not in self.locks:
            self.locks[chat_id] = asyncio.Lock()
        async with self.locks[chat_id]:
            if message == choice_list[2]:
                await self.no_players_left(game, chat_id)
                await self.last_action_change(game, message)
                return None
            user = await self.valid_user_check(game, user_id)
            if user is None:
                return None
            elif message in choice_list:
                if message != game.last_action:
                    await self.last_action_change(game, message)
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} {action_for_decision}",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
            elif not game.last_action:
                return None
            else:
                if game.last_action == choice_list[0]:
                    await self.choose_letter(
                        game, message, user, chat_id, game.players
                    )
                elif game.last_action == choice_list[1]:
                    await self.choose_word(
                        game, message, user, chat_id, game.players
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
                message=f"{user.name} {user.last_name} {choose_one_letter}",
                chat_id=chat_id,
                keyboard=await self.app.store.vk_api.get_default_keyboard(),
            )
        else:
            new_message_lower = new_message.lower()
            game.question.answer_lower = game.question.answer.lower()
            if (
                new_message_lower in game.question.answer_lower
                and new_message not in game.letters_revealed
            ):
                revealed_letters = game.letters_revealed + new_message_lower
                display_word = "".join(
                    [
                        letter if letter.lower() in revealed_letters else "-"
                        for letter in game.question.answer
                    ]
                )
                if len(set(revealed_letters)) == len(set(game.question.answer)):
                    await self.plus_points("word", game, user)
                    game = await self.get_game(chat_id + id_constant)
                    await self.game_over(user, chat_id, game)
                else:
                    counter = game.question.answer_lower.count(
                        new_message_lower
                    )
                    await self.plus_points("letter", game, user, counter)
                    await self.app.store.vk_api.send_message(
                        message=f"{display_word}. {choose_again}",
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
            elif new_message_lower in game.letters_revealed:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} {user.last_name} {letter_exist}",
                    chat_id=chat_id,
                    keyboard=await self.app.store.vk_api.get_default_keyboard(),
                )
            else:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} {failed_letter}",
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
                message=f"{user.name} {user.last_name} {chose_word}",
                chat_id=chat_id,
                keyboard=await self.app.store.vk_api.get_default_keyboard(),
            )
        else:
            if new_message.lower() == game.question.answer.lower():
                await self.plus_points("word", game, user)
                game = await self.get_game(chat_id + id_constant)
                await self.game_over(user, chat_id, game)
            else:
                await self.app.store.vk_api.send_message(
                    message=f"{user.name} {user.last_name} {user_kicked}",
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
            message=f"{user.name} {user.last_name} поздравляю вы выиграли! {game.question.answer} верный ответ! "
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
        return f"{game_leaderboard} {output}"

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
            return noone_played
        leaderboard = {
            f"{user.name} {user.last_name}": user.total_points
            for user in chat_users
        }
        output = ", ".join(
            [f"{key}: {value}" for key, value in leaderboard.items()]
        )
        return f"{total_points} {output}"

    async def plus_points(
        self, type: str, game: Game, user: User, counter: int = 1
    ) -> None:
        update_values = {
            "points": GameScore.points + counter
            if type == "letter"
            else GameScore.points + 10
        }

        await self.app.database.orm_update(
            GameScore,
            {"game_id": game.id, "user_vk_id": user.vk_id},
            update_values,
        )

    async def last_action_change(self, game: Game, new_message: str) -> None:
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"last_action": new_message},
        )

    async def get_leaderboard(self) -> list:
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
            message=f"{game_over}" f"{await self.get_game_leaderboard(game)}",
            chat_id=chat_id,
            keyboard=await self.app.store.vk_api.get_preview_keyboard(),
        )
        await self.app.database.orm_update(
            Game,
            {"id": game.id},
            {"status": "finish"},
        )

    async def valid_user_check(
        self, game: Game, user_id: int
    ) -> Optional[User]:
        user = next(
            (user for user in game.players if user.vk_id == user_id),
            None,
        )
        if user is None:
            return None
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
        return user
