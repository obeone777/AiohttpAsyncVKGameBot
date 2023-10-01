import logging
import os
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, loop_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kts_backend.store import Database
from kts_backend.store import Store
from kts_backend.web.app import setup_app
from kts_backend.web.config import Config


@pytest.fixture(scope="session")
def event_loop():
    with loop_context() as _loop:
        yield _loop


@pytest.fixture(scope="session")
def server():
    app = setup_app(
        config_path=os.path.join(
            "/Users/stanly/IT/kts_project_template/tests/config.yaml"
        )
    )
    app.on_startup.clear()
    app.on_shutdown.clear()
    app.store.vk_api.send_message = AsyncMock()

    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_shutdown.append(app.database.disconnect)

    return app


@pytest.fixture
def store(server) -> Store:
    return server.store


@pytest.fixture
def db_session(server):
    return server.database.session


@pytest.fixture(autouse=True, scope="function")
async def clear_db(server):
    yield
    try:
        session = AsyncSession(server.database._engine)
        connection = session.connection()
        for table in server.database._db.metadata.tables:
            await session.execute(text(f"TRUNCATE {table} CASCADE"))
            await session.execute(
                text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
            )

        await session.commit()
        connection.close()

    except Exception as err:
        logging.warning(err)


@pytest.fixture
def config(server) -> Config:
    return server.config


@pytest.fixture(autouse=True)
def cli(aiohttp_client, event_loop, server) -> TestClient:
    return event_loop.run_until_complete(aiohttp_client(server))


