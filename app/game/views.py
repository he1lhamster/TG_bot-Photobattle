from aiohttp_apispec import request_schema, response_schema

# from aiohttp_session import get_session
from aiohttp.web import (
    HTTPForbidden,
    HTTPUnauthorized,
    HTTPMethodNotAllowed,
    HTTPBadRequest,
    HTTPNotFound,
)
from web.app import View
from web.utils import json_response
from game.schemes import (
    GameResultSchema,
    GameSchema,
    PlayerInGameSchema,
    IsParticipantSchema,
)
from users.schemes import PlayerSchema
from web.mixins import AuthRequiredMixin
from users.models import Player


class GamesView(AuthRequiredMixin, View):
    @response_schema(GameResultSchema, 200)
    async def get(self):
        gamescores = await self.request.app.store.game.get_all_games()
        return json_response(
            data={"games": GameResultSchema().dump(gamescores, many=True)}
        )


class CreateGame(View):
    @request_schema(GameSchema)
    @response_schema(GameSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        create_game = await self.request.app.store.game.create_game(chat_id)
        if create_game:
            return json_response(data={"chat_id": chat_id})
        else:
            raise HTTPBadRequest


class JoinGame(View):
    @request_schema(PlayerInGameSchema)
    @response_schema(PlayerSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        player = Player(**data["player"])
        join_game = await self.request.app.store.game.join_game(
            chat_id=chat_id, player=player
        )
        if join_game:
            return json_response(
                data={"player": PlayerSchema().dump(join_game)}
            )
        else:
            raise HTTPBadRequest


class IsParticipant(View):
    @request_schema(PlayerInGameSchema)
    @response_schema(IsParticipantSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        player = Player(**data["player"])
        is_participant = await self.request.app.store.game.is_participant(
            chat_id=chat_id, player=player
        )
        return json_response(data={"is_participant": is_participant})


class GetCurrentGame(View):
    @response_schema(GameSchema)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        current_game_id = await self.request.app.store.game.get_current_game(
            chat_id=chat_id
        )
        if current_game_id:
            return json_response(data={"current_game_id": current_game_id})
        else:
            raise HTTPNotFound


class GetCurrentGameStatus(View):
    @response_schema(GameSchema)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        current_game_status = (
            await self.request.app.store.game.get_current_game_status(
                chat_id=chat_id
            )
        )
        if current_game_status:
            return json_response(
                data={"current_game_status": current_game_status}
            )
        else:
            raise HTTPNotFound


class GetCurrentGameState(View):
    @request_schema(GameSchema)
    @response_schema(PlayerSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        active_players = (
            await self.request.app.store.game.get_current_game_state(
                chat_id=chat_id
            )
        )

        if active_players:
            return json_response(
                data={
                    "active_players": PlayerSchema().dump(
                        active_players, many=True
                    )
                }
            )
        elif active_players == None:
            return json_response(data={"active_players": None})
        else:
            raise HTTPBadRequest


class StartGame(View):
    @request_schema(GameSchema)
    @response_schema(GameSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        start_game = await self.request.app.store.game.start_game(chat_id)
        if start_game:
            return json_response(data={"start_game": True})
        else:
            raise HTTPBadRequest


class GetLastGame(View):
    @request_schema(GameSchema)
    @response_schema(GameResultSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        last_game = await self.request.app.store.game.get_last_game(chat_id)
        if last_game != None:
            return json_response(
                data={"last_game": GameResultSchema().dump(last_game)}
            )
        else:
            raise HTTPNotFound


class FinishGame(View):
    @response_schema(PlayerSchema, 200)
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        if "winner" in data:
            winner = data["winner"]
            finish_game = await self.request.app.store.game.finish_game(
                chat_id=chat_id, winner=winner
            )
        else:
            finish_game = await self.request.app.store.game.finish_game(
                chat_id=chat_id
            )

        if finish_game:
            return json_response(
                data={"winner": PlayerSchema().dump(finish_game)}
            )
        else:
            return json_response(data={"winner": None})


class SetWinnerAndLoser(View):
    async def post(self):
        data = await self.request.json()
        chat_id = data["chat_id"]
        winner = Player(**data["winner"])
        if "loser" in data:
            loser = Player(**data["loser"])
        else:
            loser = None
        set_winner_and_loser = (
            await self.request.app.store.game.set_winner_and_loser(
                chat_id=chat_id, winner=winner, loser=loser
            )
        )
        return json_response(data={"set_winner_and_loser": True})
