from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from kts_backend.base.models import GameScore, game_user_table
from kts_backend.store.database.sqlalchemy_base import mapper_registry
from kts_backend.users.models import User


@mapper_registry.mapped
@dataclass
class QuestionAnswer:
    __tablename__ = "questions"

    __sa_dataclass_metadata_key__ = "sa"
    id: int = field(
        init=False,
        metadata={
            "sa": Column(BigInteger, primary_key=True, autoincrement=True)
        },
    )
    question_text: str = field(metadata={"sa": Column(String)})
    answer_text: str = field(metadata={"sa": Column(String)})
    games: List["Game"] = field(
        default_factory=list,
        metadata={"sa": relationship("Game", back_populates="question")},
    )


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
    chat_id: int = field(default=None, metadata={"sa": Column(BigInteger)})
    question_id: int = field(
        default=None,
        metadata={"sa": Column(BigInteger, ForeignKey("questions.id"))},
    )
    question: QuestionAnswer = field(
        default=None, metadata={"sa": relationship("QuestionAnswer")}
    )
    created_at: datetime = field(
        default_factory=datetime.utcnow, metadata={"sa": Column(DateTime)}
    )
    status: str = field(default="start", metadata={"sa": Column(String)})
    turn_user_id: int = field(default=0, metadata={"sa": Column(BigInteger)})
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
                "GameScore", foreign_keys=[game_user_table.c.game_id]
            )
        },
    )
