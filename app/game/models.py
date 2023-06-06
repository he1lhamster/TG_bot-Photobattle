from dataclasses import dataclass
from typing import Optional
from store.database.sqlalchemy_base import db
from users.models import Player
import enum
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    String,
    DateTime,
    Enum,
    BigInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


@dataclass
class Game:
    id: int
    created_at: Optional[DateTime]
    chat_id: int
    status: Optional[str]


@dataclass
class GameScore:
    game_id: int
    game_round: int
    player_id: int
    player_status: int


@dataclass
class GameResult:
    game_id: int
    chat_id: int
    winner: Optional[Player]
    players: list[Player]


class GameModel(db):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, autoincrement="auto")
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    chat_id = Column(BigInteger, nullable=False)
    players = relationship(
        "PlayerModel", secondary="gamescores", back_populates="games"
    )
    status = Column(Enum("CREATED", "STARTED", "FINISHED", name="status"))


class GameScoreModel(db):
    __tablename__ = "gamescores"
    id = Column(Integer, primary_key=True, autoincrement="auto")
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"))
    player_status = Column(Integer, default=1)
    game_round = Column(Integer, default=0)
