from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from kts_backend.game.models import GameModel
from kts_backend.store.vk_api.datas import (
    Message,
    Update,
    UpdateObject,
    UpdateMessage,
)
from kts_backend.users.models import UserModel
from tests.utils import check_empty_table_exists


@pytest.mark.asyncio
class TestHandleUpdates:
    async def test_no_messages(self, store):
        await store.bots_manager.handle_updates(updates=[])
        assert store.vk_api.send_message.called is False

    async def test_new_message(self, store):
        await store.bots_manager.handle_updates(
            updates=[
                Update(
                    type="message_new",
                    object=UpdateObject(
                        UpdateMessage(id=1, from_id=1, peer_id=1, text="bla")
                    ),
                )
            ]
        )
        assert store.vk_api.send_message.call_count == 1
        message: Message = store.vk_api.send_message.mock_calls[0].args[0]
        assert message.user_id == 1
        assert message.text == "bla"


@pytest.mark.asyncio
class TestDatabase:
    async def test_table_exists(self, cli):
        await check_empty_table_exists(cli, "users")
        await check_empty_table_exists(cli, "games")
        await check_empty_table_exists(cli, "game_user")
        await check_empty_table_exists(cli, "questions")

    async def test_game_create(cli, db_session, store):
        chat_id = 12345
        existing_users = [
            UserModel(vk_id=1, name="Alice", last_name="Smith"),
            UserModel(vk_id=2, name="Bob", last_name="Johnson"),
        ]
        async with db_session() as session:
            with patch(
                "kts_backend.store.vk_api.accessor.VkApiAccessor.get_conversation_members",
                return_value=existing_users,
            ):
                game = await store.vk_api.game_create(chat_id)
            assert game is not None
            assert game.chat_id == chat_id
            assert game.id is not None
            assert game.created_at is not None
            assert len(game.players) == len(existing_users)
            player_vk_ids = {player.user_id for player in game.players}
            assert player_vk_ids == {1, 2}
            users_in_db = (
                (
                    await session.execute(
                        select(UserModel).where(UserModel.vk_id.in_([1, 2]))
                    )
                )
                .scalars()
                .all()
            )
            assert set(u.vk_id for u in users_in_db) == {1, 2}
            game_in_db = (
                await session.execute(
                    select(GameModel)
                    .where(GameModel.chat_id == chat_id)
                    .limit(1)
                )
            ).scalar()
            assert game_in_db is not None
            assert game_in_db.chat_id == chat_id

    async def test_get_game_by_chat_id(cli, clear_db, game1, store):
        gamef = await game1
        chat_id = 12345
        result = await store.vk_api.get_game_by_chatid(chat_id=chat_id)
        assert result is not None
        from kts_backend.game.models import Game

        assert isinstance(result, Game)
        assert result.id == 1
        assert result.created_at == datetime.strptime(
            "2023-01-01T12:34:56Z", "%Y-%m-%dT%H:%M:%SZ"
        )
        assert result.chat_id == chat_id
        assert result.status == True

        assert len(result.players) == 2
        assert result.players[0].user_id == 1
        assert result.players[0].points == 10
        assert result.players[0].user_is_active == True
        assert result.players[0].user_turn == False

        assert result.players[1].user_id == 2
        assert result.players[1].points == 15
        assert result.players[1].user_is_active == True
        assert result.players[1].user_turn == True

    async def test_get_game_by_incorrect_chat_id(cli, clear_db, game1, store):
        gamef = await game1
        chat_id = 1111
        result = await store.vk_api.get_game_by_chatid(chat_id=chat_id)
        assert result is None
