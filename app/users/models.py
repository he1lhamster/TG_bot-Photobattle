from dataclasses import dataclass
from typing import Optional
from store.database.sqlalchemy_base import db
from sqlalchemy import Column, Integer, String, BigInteger
from sqlalchemy.orm import relationship
from hashlib import sha256


@dataclass
class Player:
    id: int  # tg id
    username: Optional[str]
    photo_file_id: Optional[str] = None


@dataclass
class Admin:
    id: int
    email: str
    password: Optional[str] = None

    def is_password_valid(self, password: str):
        return self.password == sha256(password.encode()).hexdigest()

    @classmethod
    def from_session(cls, session: Optional[dict]) -> Optional["Admin"]:
        return cls(id=session["admin"]["id"], email=session["admin"]["email"])


class PlayerModel(db):
    __tablename__ = "players"
    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=False)
    games = relationship(
        "GameModel",
        secondary="gamescores",
        back_populates="players",
    )
    photo_file_id = Column(String, nullable=False)


class AdminModel(db):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True)
    password = Column(String)
