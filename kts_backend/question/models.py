from dataclasses import dataclass, field

from sqlalchemy import Column, BigInteger, String

from kts_backend.store.database import mapper_registry


@mapper_registry.mapped
@dataclass
class Question:
    __tablename__ = "questions"

    __sa_dataclass_metadata_key__ = "sa"
    id: int = field(
        init=False,
        metadata={
            "sa": Column(BigInteger, primary_key=True, autoincrement=True)
        },
    )
    question: str = field(metadata={"sa": Column(String)})
    answer: str = field(metadata={"sa": Column(String)})
