from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship

from kts_backend.store.database.sqlalchemy_base import db


if TYPE_CHECKING:
    from kts_backend.game.models import GameScore


@dataclass
class User:
    vk_id: int
    name: str
    last_name: str
    games: List["GameScore"] = field(default_factory=list)


class UserModel(db):
    __tablename__ = "users"
    vk_id = Column(BigInteger, primary_key=True)
    name = Column(String)
    last_name = Column(String)
    games = relationship("GameModel", secondary="game_user", back_populates="players")






