from typing import Optional, TYPE_CHECKING
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text

from store.database.sqlalchemy_base import db

if TYPE_CHECKING:
    from web.app import Application


class Database:
    def __init__(self, app: "Application"):
        self.app = app
        # self._engine: Optional[AsyncEngine] = None
        # self._db: Optional[declarative_base] = None
        # self.session: Optional[AsyncSession] = None
        # self.connect()

    async def connect(self, *_: list, **__: dict) -> None:
        self._db = db
        self._engine = create_async_engine(
            f"postgresql+asyncpg://{self.app.config.database.user}:"
            f"{self.app.config.database.password}@{self.app.config.database.host}"
            f"/{self.app.config.database.database}"
        )
        self.session = sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        print("Connected to Database", self.session)

    async def disconnect(self, *_: list, **__: dict) -> None:
        pass
