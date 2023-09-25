# from typing import Sequence, Callable

from aiohttp.web import (
    Application as AiohttpApplication,
    # View as AiohttpView,
    Request as AiohttpRequest,
)
from typing import Optional


# from kts_backend import __appname__, __version__
from .config import setup_config, Config
from .logger import setup_logging
from .mw import setup_middlewares
from kts_backend.store import Store, setup_store, Database


# from .urls import register_urls


# __all__ = ("ApiApplication",)


class Application(AiohttpApplication):
    config: Optional[Config] = None
    store: Optional[Store] = None
    database: Optional[Database] = None


class Request(AiohttpRequest):
    # admin: Optional[Admin] = None

    @property
    def app(self) -> Application:
        return super().app()


app = Application()


def setup_app(config_path: str) -> Application:
    setup_logging(app)
    setup_config(app, config_path)
    # session_setup(app, EncryptedCookieStorage(app.config.session.key))
    # setup_routes(app)
    # setup_aiohttp_apispec(
    #     app, title="Vk Quiz Bot", url="/docs/json", swagger_path="/docs"
    # )
    setup_middlewares(app)
    setup_store(app)
    return app
