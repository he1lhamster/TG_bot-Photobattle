from aiohttp.web_app import Application

import typing

from game.views import (
    GamesView,
    CreateGame,
    JoinGame,
    IsParticipant,
    GetCurrentGame,
    GetCurrentGameStatus,
    GetCurrentGameState,
    StartGame,
    GetLastGame,
    FinishGame,
    SetWinnerAndLoser,
)

if typing.TYPE_CHECKING:
    from web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/game_list", GamesView)
    app.router.add_view("/create_game", CreateGame)
    app.router.add_view("/join_game", JoinGame)
    app.router.add_view("/is_participant", IsParticipant)
    app.router.add_view("/get_current_game", GetCurrentGame)
    app.router.add_view("/get_current_game_status", GetCurrentGameStatus)
    app.router.add_view("/get_current_game_state", GetCurrentGameState)
    app.router.add_view("/start_game", StartGame)
    app.router.add_view("/get_last_game", GetLastGame)
    app.router.add_view("/finish_game", FinishGame)
    app.router.add_view("/set_winner_and_loser", SetWinnerAndLoser)
