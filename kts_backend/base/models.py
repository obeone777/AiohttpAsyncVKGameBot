from sqlalchemy import Table, BigInteger, Column, ForeignKey

from kts_backend.store.database.sqlalchemy_base import db

game_user_association = Table(
    "game_user",
    db.metadata,
    Column("game_id", BigInteger, ForeignKey("games.id"), primary_key=True),
    Column("user_vk_id", BigInteger, ForeignKey("users.vk_id"), primary_key=True),
    Column("points", BigInteger)
)