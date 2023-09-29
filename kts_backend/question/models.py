from dataclasses import dataclass, field
from typing import List

from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship

from kts_backend.store.database import mapper_registry


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
