from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kts_backend.game.models import Game
from kts_backend.base.models import GameScore
from kts_backend.users.models import User

@pytest.fixture
async def game1(db_session: AsyncSession):
    game = Game(
        id=1,
        created_at=datetime.strptime(
            "2023-01-01T12:34:56Z", "%Y-%m-%dT%H:%M:%SZ"
        ),
        chat_id=12345,
        status="start",
    )
    gamescore1 = GameScore(
        game_id=1, user_vk_id=1, points=10, user_is_active=True
    )
    gamescore2 = GameScore(
        game_id=1, user_vk_id=2, points=15, user_is_active=True
    )
    user1 = User(vk_id=1, name="Alice", last_name="Smith")
    user2 = User(vk_id=2, name="Bob", last_name="Johnson")

    async with db_session.begin() as session:
        session.add(game)
        await session.flush()
        session.add_all([user1, user2])
        await session.flush()
        session.add_all([gamescore1, gamescore2])