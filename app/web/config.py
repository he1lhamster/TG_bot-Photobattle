import typing
from dataclasses import dataclass

import yaml

if typing.TYPE_CHECKING:
    from web.app import Application


@dataclass
class BotConfig:
    token: str


@dataclass
class SessionConfig:
    key: str


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "game_kts"


@dataclass
class AdminConfig:
    email: str
    password: str


@dataclass
class Config:
    admin: AdminConfig
    bot: BotConfig = None
    database: DatabaseConfig = None
    session: SessionConfig = None


def setup_config(app: "Application", config_path: str):
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    app.config = Config(
        bot=BotConfig(
            token=raw_config["bot"]["token"],
        ),
        session=SessionConfig(
            key=raw_config["session"]["key"],
        ),
        database=DatabaseConfig(**raw_config["database"]),
        admin=AdminConfig(
            email=raw_config["admin"]["email"],
            password=raw_config["admin"]["password"],
        ),
    )
