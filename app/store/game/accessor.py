import typing
from typing import Optional, Union
from datetime import datetime

from base.base_accessor import BaseAccessor
from users.models import Player, PlayerModel
from game.models import (
    GameModel,
    GameScore,
    Game,
    GameScoreModel,
    GameResult,
)
from sqlalchemy import select, func, update, join


if typing.TYPE_CHECKING:
    from web.app import Application


class GameAcessor(BaseAccessor):
    async def create_game(self, chat_id: int):
        """
        assert that no games unfinished in this chat. If not - finish that game
        create new record in db with "CREATED" status
        """
        async with self.app.database.session.begin() as Session:
            cur_game = await self.get_current_game(chat_id)
            if cur_game:
                await self.finish_game(chat_id)
            # await Session.execute(
            #     text(
            #         f"insert into games (chat_id, status) values ({chat_id}, 'CREATED')"
            #     )
            # )
            new_game = GameModel(chat_id=chat_id, status="CREATED")
            Session.add(new_game)

            await Session.commit()
            return True  # return for api - game is created

    async def join_game(self, player: Player, chat_id: int) -> Optional[Player]:
        """
        trying to get player from db
        1) not exist: get profile photo -> create new db record
        2) exist: get profile photo -> update existing record
        !!! Assuming players won't delete their photo from telegram
        !!! during game session, store only file_id
        if no profile photo - return None, else return player (existed or created)
        """
        current_game = await self.get_current_game(chat_id)

        if not current_game:
            return None

        player_id = player.id
        new_player = await self.app.store.user.get_user_by_id(player_id)

        async with self.app.database.session.begin() as Session:
            if not new_player:  # if not exist - create in db
                new_player = await self.app.store.user.create_user(player)
                if not new_player:
                    return None
            else:
                already_in_game = await self.is_participant(
                    player=new_player, chat_id=chat_id
                )
                if already_in_game:
                    await Session.commit()
                    return new_player

                photo_id = new_player.photo_file_id
                if (
                    not photo_id
                ):  # user MUST have avatar, replace current db value
                    return None
                else:
                    # await Session.execute(
                    #     text(
                    #         f"update players set photo_file_id='{photo_id}' where id={new_player.id}"
                    #     )
                    # )
                    await Session.execute(
                        update(PlayerModel)
                        .where(PlayerModel.id == new_player.id)
                        .values(photo_file_id=photo_id)
                    )

            # await Session.execute(
            #     text(
            #         f"insert into gamescores (game_id, player_id, player_status, game_round) "
            #         f"values ({current_game}, {new_player.id}, 1, 0)"
            #     )
            # )
            gamescore = GameScoreModel(
                game_id=current_game,
                player_id=new_player.id,
                player_status=1,
                game_round=0,
            )
            Session.add(gamescore)

            await Session.commit()
            return new_player

    async def is_participant(self, player: Player, chat_id: int) -> bool | None:
        """
        check if player already patricipant of current game in this chat
        """
        current_game_id = await self.get_current_game(chat_id)
        if current_game_id:
            async with self.app.database.session.begin() as Session:
                # count = await Session.execute(
                #     text(
                #         f"select count(1) from gamescores where game_id={current_game_id} and player_id={player.id}"
                #     )
                # )
                # count = count.mappings().fetchone()["count"]
                count = await Session.execute(
                    select(func.count(1)).where(
                        (GameScoreModel.game_id == current_game_id)
                        & (GameScoreModel.player_id == player.id)
                    )
                )
                count = count.mappings().fetchone()["count"]

                return False if count == 0 else True
        else:
            return None

    async def get_current_game(
        self, chat_id: int
    ) -> Optional[int]:  # GameModel.id
        """
        select current game session from db, return game.id == gamescores.game_id
        """
        async with self.app.database.session.begin() as Session:
            # current_game = await Session.execute(
            #     text(
            #         f"select id from games where status!='FINISHED' and chat_id={chat_id};"
            #     )
            # )
            # current_game = current_game.mappings().fetchone()
            current_game = await Session.execute(
                select(GameModel.id).where(
                    (GameModel.status != "FINISHED")
                    & (GameModel.chat_id == chat_id)
                )
            )
            current_game_id = current_game.mappings().fetchone()

            if not current_game_id:  # no current_games
                return None
            else:
                return current_game_id["id"]

    async def get_current_game_status(self, chat_id: int) -> Optional[str]:
        """
        select current game session from db, return game.status
        """
        async with self.app.database.session.begin() as Session:
            # current_status = await Session.execute(
            #     text(
            #         f"select status from games where chat_id={chat_id} and status!='FINISHED';"
            #     )
            # )
            # current_status = current_status.mappings().fetchone()
            current_status = await Session.execute(
                select(GameModel.status).where(
                    (GameModel.status != "FINISHED")
                    & (GameModel.chat_id == chat_id)
                )
            )
            current_status = current_status.mappings().fetchone()

            if not current_status:  # no current_statuss
                return None
            else:
                assert len(current_status) == 1  # only one current game
                return current_status["status"]

    async def start_game(self, chat_id: int):
        """
        set current game status to Started
        """
        current_game = await self.get_current_game(chat_id)
        async with self.app.database.session.begin() as Session:
            # await Session.execute(
            #     text(
            #         f"update games set status='STARTED' where id={current_game}"
            #     )
            # )
            # game = await Session.query(GameModel).where(id=current_game).scalar()
            # game.status = "STARTED"
            await Session.execute(
                update(GameModel)
                .where(GameModel.id == current_game)
                .values(status="STARTED")
            )
            await Session.commit()

    async def get_current_game_state(self, chat_id) -> list[Player] | None:
        """
        assuming current_game.status != 'FINISHED'
        find all active players (with player_status 1) and with minimal unfinished round number
        return list of active players
        """
        current_game_id = await self.get_current_game(chat_id)

        async with self.app.database.session.begin() as Session:
            if current_game_id:
                # active_players_db = await Session.execute(
                #     text(
                #         f"select players.id, players.username, "
                #         f"players.photo_file_id, gamescores.game_round from players "
                #         f"left join gamescores on gamescores.player_id = players.id "
                #         f"left join games on gamescores.game_id=games.id "
                #         f"where gamescores.game_id = {current_game_id} and gamescores.player_status = 1 "
                #         f"and gamescores.game_round=(select min(game_round) from gamescores where (game_id={current_game_id} "
                #         f"                        and gamescores.player_status = 1)) "
                #         f"and games.status != 'FINISHED'"
                #     )
                # )
                # active_players = active_players_db.mappings().all()
                min_round = await Session.execute(
                    select(func.min(GameScoreModel.game_round)).where(
                        (GameScoreModel.game_id == current_game_id)
                        & (GameScoreModel.player_status == 1)
                    )
                )
                min_round = min_round.mappings().fetchone()["min"]

                query = (
                    select(
                        PlayerModel.id,
                        PlayerModel.username,
                        PlayerModel.photo_file_id,
                        GameScoreModel.game_round,
                    )
                    .select_from(PlayerModel)
                    .join(
                        GameScoreModel,
                        GameScoreModel.player_id == PlayerModel.id,
                    )
                    .join(GameModel, GameScoreModel.game_id == GameModel.id)
                    .where(
                        (
                            (GameScoreModel.game_id == current_game_id)
                            & (GameScoreModel.player_status == 1)
                            & (GameScoreModel.game_round == min_round)
                            & (GameModel.status != "FINISHED")
                        )
                    )
                )

                active_players = await Session.execute(query)
                active_players = active_players.fetchall()

                if active_players:
                    active_players = [
                        Player(
                            id=p.id,
                            username=p.username,
                            photo_file_id=p.photo_file_id,
                        )
                        for p in active_players
                    ]
                    return active_players
                else:
                    return None
            else:
                return None

    @staticmethod
    def players_and_winners(
        players_raw: list,
    ) -> Union[list[Player], Player | None]:
        """
        received list from joined tables and return list[Player] and winner, if exist
        """
        players = []
        winner = None

        for player in players_raw:
            players.append(
                Player(
                    id=player["player_id"],
                    username=player["username"],
                    # photo_file_id=player.photo_file_id
                )
            )
            if player["player_status"] == 1:
                assert winner == None  # can't be two winners
                winner = Player(
                    id=player["player_id"],
                    username=player["username"],
                    # photo_file_id=winner.photo_file_id
                )
        return players, winner

    async def get_last_game(self, chat_id: str) -> Optional[GameResult]:
        """
        return last finished game statistic from db.gamescores in this chat
        can use created_at, bc no 2 running game at the same time
        """
        async with self.app.database.session.begin() as Session:
            # last_game = await Session.execute(
            #     text(
            #         f"select games.id as game_id, players.id as player_id, "
            #         f"players.username as username, gamescores.player_status from games "
            #         f"left join gamescores on gamescores.game_id = games.id "
            #         f"left join players on gamescores.player_id = players.id "
            #         f"where games.chat_id={chat_id} "
            #         f"and games.id= (select max(games.id) from games where games.status='FINISHED');"
            #     )
            # )
            last_game_id = await Session.execute(
                select(func.max(GameModel.id)).where(
                    (GameModel.status == "FINISHED")
                    & (GameModel.chat_id == chat_id)
                )
            )
            last_game_id = last_game_id.mappings().fetchone()["max"]

            last_game = await Session.execute(
                select(
                    GameModel.id.label("game_id"),
                    PlayerModel.id.label("player_id"),
                    PlayerModel.username.label("username"),
                    GameScoreModel.player_status,
                )
                .join(GameScoreModel, GameScoreModel.game_id == GameModel.id)
                .join(PlayerModel, PlayerModel.id == GameScoreModel.player_id)
                .where(
                    (GameModel.chat_id == chat_id)
                    & (GameModel.id == last_game_id)
                )
            )

            last_game = last_game.mappings().fetchall()

            if last_game:
                game_id = last_game[0]["game_id"]
                players, winner = self.players_and_winners(last_game)
                last_game_result = GameResult(
                    game_id=game_id,
                    chat_id=chat_id,
                    winner=winner,
                    players=players,
                )
                return last_game_result
            else:
                return None

    async def get_all_games(
        self,
    ) -> list[GameResult] | None:  # game_id, chat_id, winner, players[]
        """
        return list with all records in gamescores like list of GameResult
        one finished game = one GameResult obj
        """
        async with self.app.database.session.begin() as Session:
            # finished_games = await Session.execute(
            #     text(
            #         "select distinct id, chat_id from games where status='FINISHED';"
            #     )
            # )
            # finished_games = finished_games.mappings().all()

            finished_games = await Session.execute(
                select(GameModel.id, GameModel.chat_id).distinct()
            )
            finished_games = finished_games.mappings().fetchall()

            if finished_games:
                all_games = []
                for f_game in finished_games:
                    game_id = f_game["id"]
                    chat_id = f_game["chat_id"]
                    # players_raw = await Session.execute(
                    #     text(
                    #         f"select players.id as player_id, players.username as username, "
                    #         f"gamescores.player_status from players "
                    #         f"left join gamescores on gamescores.player_id=players.id "
                    #         f"where gamescores.game_id={game_id}; "
                    #     )
                    # )
                    # # players_raw = players_raw.mappings().all()
                    # players_raw = (await Session.query(PlayerModel.id.label("player_id"), PlayerModel.username.label("username"), GameScoreModel.player_status)
                    #                .join(GameScoreModel, GameScoreModel.player_id == PlayerModel.id)
                    #                .where(GameScoreModel.game_id == game_id)
                    # ).all()
                    players_raw = await Session.execute(
                        select(
                            PlayerModel.id.label("player_id"),
                            PlayerModel.username.label("username"),
                            GameScoreModel.player_status,
                        )
                        .join(
                            GameScoreModel,
                            GameScoreModel.player_id == PlayerModel.id,
                        )
                        .where(GameScoreModel.game_id == game_id)
                    )
                    players_raw = players_raw.mappings().fetchall()

                    players, winner = self.players_and_winners(players_raw)
                    all_games.append(
                        GameResult(
                            game_id=game_id,
                            chat_id=chat_id,
                            players=players,
                            winner=winner,
                        )
                    )
                return all_games
            else:
                return None

    async def finish_game(
        self, chat_id: int, winner: Optional[Player] = None
    ) -> Optional[Player]:
        """
        get current game by chat_id, if get -> set status to "FINISHED"
        if winner: return winner
            (assert select count(status) where game_id=current_game_id; == 1)
        else: return none
            set all user status in this game to 0 (lose)
        """
        current_game_id = await self.get_current_game(chat_id)

        if current_game_id:
            async with self.app.database.session.begin() as Session:
                # await Session.execute(
                #     text(
                #         f"update games set status='FINISHED' where id={current_game_id}"
                #     )
                # )
                await Session.execute(
                    update(GameModel)
                    .where(GameModel.id == current_game_id)
                    .values(status="FINISHED")
                )

                if winner:
                    # winners_count = await Session.execute(
                    #     text(
                    #         f"select sum(player_status) from gamescores where game_id={current_game_id};"
                    #     )
                    # )
                    winners_count = await Session.execute(
                        select(func.sum(GameScoreModel.player_status)).where(
                            GameScoreModel.game_id == current_game_id
                        )
                    )
                    winners_count = winners_count.mappings().fetchone()["sum"]
                    assert winners_count == 1
                    await Session.commit()
                    return winner
                else:  # no winner, unfinished game
                    # await Session.execute(
                    #     text(
                    #         f"update gamescores set player_status=0 where game_id={current_game_id};"
                    #     )
                    # )
                    await Session.execute(
                        update(GameScoreModel)
                        .where(GameScoreModel.game_id == current_game_id)
                        .values(player_status=0)
                    )
                    await Session.commit()
                    return None
        else:
            return None

    async def set_winner_and_loser(
        self, chat_id: int, winner: Player, loser: Optional[Player] = None
    ):
        """
        called after each pair-round,
        set status to loser = 0, set round to winner += 1
        """
        current_game = await self.get_current_game(chat_id)
        async with self.app.database.session.begin() as Session:
            # await Session.execute(
            #     text(
            #         f"update gamescores set game_round=game_round+1 where player_id={winner.id} and game_id={current_game}"
            #     )
            # )
            await Session.execute(
                update(GameScoreModel)
                .where(
                    (
                        (GameScoreModel.player_id == winner.id)
                        & (GameScoreModel.game_id == current_game)
                    )
                )
                .values(game_round=(GameScoreModel.game_round + 1))
            )

            if loser:
                # await Session.execute(
                #     text(
                #         f"update gamescores set player_status=0 where player_id={loser.id} and game_id={current_game}"
                #     )
                # )
                await Session.execute(
                    update(GameScoreModel)
                    .where(
                        (
                            (GameScoreModel.player_id == loser.id)
                            & (GameScoreModel.game_id == current_game)
                        )
                    )
                    .values(player_status=0)
                )
            await Session.commit()
