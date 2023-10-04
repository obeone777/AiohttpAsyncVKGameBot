from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship

from kts_backend.base.models import game_user_table
from kts_backend.store.database.sqlalchemy_base import mapper_registry

if TYPE_CHECKING:
    from kts_backend.game.models import Game


@mapper_registry.mapped
@dataclass
class User:
    __tablename__ = "users"

    __sa_dataclass_metadata_key__ = "sa"
    vk_id: int = field(metadata={"sa": Column(BigInteger, primary_key=True)})
    name: str = field(metadata={"sa": Column(String)})
    last_name: str = field(metadata={"sa": Column(String)})
    total_points: int = field(default=0, metadata={"sa": Column(BigInteger)})
    games: List["Game"] = field(
        default_factory=list,
        metadata={
            "sa": relationship(
                "Game", secondary=game_user_table
            )
        },
    )
