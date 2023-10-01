from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from kts_backend.base.models import GameScore, game_user_table
from kts_backend.question.models import Question
from kts_backend.store.database.sqlalchemy_base import mapper_registry
from kts_backend.users.models import User


@mapper_registry.mapped
@dataclass
class Game:
    __tablename__ = "games"

    __sa_dataclass_metadata_key__ = "sa"
    id: int = field(
        init=False,
        metadata={
            "sa": Column(BigInteger, primary_key=True, autoincrement=True)
        },
    )
    chat_id: int = field(metadata={"sa": Column(BigInteger)})
    question_id: int = field(
        default=None,
        metadata={"sa": Column(BigInteger, ForeignKey("questions.id"))},
    )
    question: Question = field(
        default=None, metadata={"sa": relationship("Question")}
    )
    created_at: datetime = field(
        default_factory=datetime.utcnow, metadata={"sa": Column(DateTime)}
    )
    status: str = field(default="start", metadata={"sa": Column(String)})
    turn_user_id: Optional[int] = field(default=None, metadata={"sa": Column(BigInteger, nullable=True)})
    players: List[User] = field(
        default_factory=list,
        metadata={
            "sa": relationship(
                "User", secondary=game_user_table, back_populates="games"
            )
        },
    )
    scores: List[GameScore] = field(
        default_factory=list,
        metadata={
            "sa": relationship(
                "GameScore", foreign_keys=[game_user_table.c.game_id], overlaps="games,players"
            )
        },
    )
    letters_revealed: str = field(default="", metadata={"sa": Column(String)})
    last_action: str = field(default="", metadata={"sa": Column(String)})
