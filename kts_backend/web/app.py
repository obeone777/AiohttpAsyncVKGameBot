from aiohttp.web import (
    Application as AiohttpApplication,
    Request as AiohttpRequest,
)
from typing import Optional

from .config import setup_config, Config
from .logger import setup_logging
from .mw import setup_middlewares
from kts_backend.store import Store, setup_store, Database


class Application(AiohttpApplication):
    config: Optional[Config] = None
    store: Optional[Store] = None
    database: Optional[Database] = None


class Request(AiohttpRequest):
    @property
    def app(self) -> Application:
        return super().app()


app = Application()


def setup_app(config_path: str) -> Application:
    setup_logging(app)
    setup_config(app, config_path)
    setup_middlewares(app)
    setup_store(app)
    return app
