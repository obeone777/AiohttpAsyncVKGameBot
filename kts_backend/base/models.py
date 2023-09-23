from dataclasses import dataclass

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey

from kts_backend.store.database.sqlalchemy_base import db


@dataclass
class GameScore:
    user_vk_id: int
    game_id: int
    points: int = 0
    user_is_active: bool = True
    user_turn: bool = False


class GameUserAssociation(db):
    __tablename__ = 'game_user'
    game_id = Column(BigInteger, ForeignKey('games.id'), primary_key=True)
    user_vk_id = Column(BigInteger, ForeignKey('users.vk_id'), primary_key=True)
    points = Column(BigInteger, default=0)
    user_is_active = Column(Boolean, default=True)
    user_turn = Column(Boolean, default=False)

