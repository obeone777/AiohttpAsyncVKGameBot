from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from sqlalchemy import Column, BigInteger, DateTime
from sqlalchemy.orm import relationship

from kts_backend.base.models import game_user_association
from kts_backend.store.database.sqlalchemy_base import db


@dataclass
class GameScore:
    points: int
    user_id: int
    game_id: int

@dataclass
class Game:
    id: int
    created_at: datetime
    chat_id: int
    players: List[int] = field(default_factory=list)
    scores: List[GameScore] = field(default_factory=list)


class GameModel(db):
    __tablename__ = "games"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    chat_id = Column(BigInteger)
    players = relationship("User", secondary=game_user_association, back_populates="games")