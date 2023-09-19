from typing import TYPE_CHECKING, List, Optional, TypeVar, Union

from sqlalchemy.engine import ChunkedIteratorResult
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from kts_backend.store.database.sqlalchemy_base import db


if TYPE_CHECKING:
    from kts_backend.web.app import Application


class Database:
    def __init__(self, app: "Application"):
        self.app = app
        self._engine: Optional[AsyncEngine] = None
        self._db: Optional[declarative_base] = None
        self.session: Optional[AsyncSession] = None

    @property
    def url_for_db(self):
        db_settings = self.app.config.database
        return f"postgresql+asyncpg://{db_settings.user}:{db_settings.password}@{db_settings.host}/{db_settings.database}"

    async def connect(self, *_: list, **__: dict) -> None:
        self._db = db
        self._engine = create_async_engine(self.url_for_db, echo=True, future=True)
        self.session = sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def disconnect(self, *_: list, **__: dict) -> None:
        if self._engine:
            await self._engine.dispose()

    async def orm_add(self, obj: Union[TypeVar, List[TypeVar]]):
        async with self.session() as session:
            if isinstance(obj, list):
                session.add_all(obj)
            else:
                session.add(obj)
            await session.commit()

    async def orm_select(self, query) -> ChunkedIteratorResult:
        async with self.session() as session:
            result: ChunkedIteratorResult = await session.execute(query)
            return result
