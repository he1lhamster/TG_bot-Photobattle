from typing import Sequence, Callable, Optional

from aiohttp.web import (
    Application as AiohttpApplication,
    View as AiohttpView,
    Request as AiohttpRequest,
)

from aiohttp_apispec import setup_aiohttp_apispec
from store import Store, setup_store
from web.config import Config, setup_config
from store.database.database import Database
from users.models import Admin
from web.middlewares import setup_middlewares
from web.routes import setup_routes
from web.logger import setup_logging

from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage


__all__ = ("ApiApplication",)


class Application(AiohttpApplication):
    config: Optional[Config] = None
    store: Optional[Store] = None
    database: Optional[Database] = None


class Request(AiohttpRequest):
    admin: Optional[Admin] = None

    @property
    def app(self) -> Application:
        return super().app()


class View(AiohttpView):
    @property
    def request(self) -> Request:
        return super().request

    @property
    def database(self):
        return self.request.app.database

    @property
    def store(self) -> Store:
        return self.request.app.store

    @property
    def data(self) -> dict:
        return self.request.get("data", {})


app = Application()


def setup_app(config_path: str) -> Application:
    setup_aiohttp_apispec(
        app, title="Tg PhotoBattle Bot", url="/docs/json", swagger_path="/docs"
    )
    setup_logging(app)
    setup_config(app, config_path)
    setup_routes(app)
    session_setup(app, EncryptedCookieStorage(app.config.session.key))
    setup_middlewares(app)
    setup_store(app)
    return app
