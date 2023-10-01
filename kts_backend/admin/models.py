from dataclasses import field, dataclass
from hashlib import sha256
from typing import Optional

from sqlalchemy import Column, BigInteger, String

from kts_backend.store.database.sqlalchemy_base import mapper_registry


@mapper_registry.mapped
@dataclass
class Admin:
    __tablename__ = "admins"
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(
        init=False,
        metadata={
            "sa": Column(BigInteger, primary_key=True, autoincrement=True)
        },
    )
    email: str = field(
        metadata={"sa": Column(String, nullable=False, unique=True)}
    )
    password: Optional[str] = field(
        default=None, metadata={"sa": Column(String, nullable=False)}
    )

    @classmethod
    def from_session(cls, session: Optional[dict]) -> Optional["Admin"]:
        return cls(id=session["admin"]["id"], email=session["admin"]["email"])

    @staticmethod
    def hash_password(password: str) -> str:
        return sha256(password.encode()).hexdigest()

    def pass_valid_check(self, password: str) -> bool:
        return self.password == self.hash_password(password)
