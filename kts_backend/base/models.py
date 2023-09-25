from dataclasses import dataclass

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Table, MetaData

from kts_backend.store.database.sqlalchemy_base import mapper_registry


@dataclass
class GameScore:
    user_vk_id: int
    game_id: int
    points: int = 0
    user_is_active: bool = True


metadata = MetaData()

game_user_table = Table(
    "game_user",
    mapper_registry.metadata,
    Column("game_id", BigInteger, ForeignKey("games.id"), primary_key=True),
    Column(
        "user_vk_id", BigInteger, ForeignKey("users.vk_id"), primary_key=True
    ),
    Column("points", BigInteger, default=0),
    Column("user_is_active", Boolean, default=True),
)

mapper_registry.map_imperatively(GameScore, game_user_table)
