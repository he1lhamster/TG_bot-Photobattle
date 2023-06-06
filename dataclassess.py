from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    id: int  # tg id
    username: Optional[str]
    photo_file_id: Optional[str] = None


@dataclass
class UpdateObject:
    id: int
    user: Player
    chat_id: str
    text: str
    data: Optional[str] = None
    callback_query_id: Optional[str] = None


@dataclass
class Update:
    id: int
    type: str
    object: UpdateObject


@dataclass
class Message:
    chat_id: Optional[int]
    text: Optional[str]
    reply_markup: Optional[str] = None
    message_type: Optional[str] = "message"


@dataclass
class MessageAnswerCallback:
    text: Optional[str] = None
    callback_query_id: Optional[int] = None
    show_alert: Optional[bool] = False
    message_type: Optional[str] = "messageAnswerCallback"


@dataclass
class MessageToDelete:
    chat_id: Optional[int]
    message_id: int
    message_type: Optional[str] = "messageToDelete"


@dataclass
class MessageMediaGroup:
    chat_id: int
    media: list[dict]
    message_type: Optional[str] = "messageMediaGroup"


@dataclass
class MessagePhoto:
    chat_id: int
    photo: str
    caption: Optional[str] = None
    message_type: Optional[str] = "messagePhoto"


@dataclass
class GetUserAvatar:
    user_id: int
    message_type: Optional[str] = "getUserAvatar"
