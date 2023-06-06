import asyncio
from asyncio import Task
from typing import Optional, Any
from dataclassess import (
    Update,
    UpdateObject,
    Player,
    Message,
    MessageAnswerCallback,
    MessageMediaGroup,
    MessagePhoto,
    MessageToDelete,
    GetUserAvatar,
)
import aio_pika
import json
import random
import uuid
from dataclasses import asdict
from aiohttp.client import ClientSession
from aiohttp import TCPConnector


TIMEOUT = 60
VOTING_TIMER = 15


class Manager:
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.get_updates_task: Optional[Task] = None
        self.queue_incoming_updates: Optional[aio_pika.Queue] = None
        self.queue_outcoming_messages: Optional[aio_pika.Queue] = None
        self.session: Optional[ClientSession] = None
        self.votings = {}
        self.last_inline = {}

    async def start(self):
        while self.connection is None:
            try:
                self.connection = await aio_pika.connect(
                    "amqp://guest:guest@rabbitmq:5673/"
                )
                self.channel = await self.connection.channel()
                self.exchange = await self.channel.declare_exchange(
                    "ManagerTG", auto_delete=True
                )
                self.queue_incoming_updates = await self.channel.declare_queue(
                    "incoming_updates",
                )
                self.queue_outcoming_messages = (
                    await self.channel.declare_queue("outcoming_messages")
                )
            except aio_pika.exceptions.AMQPConnectionError:
                # retry after 3 sec
                await asyncio.sleep(3)
        self.get_updates_task = asyncio.create_task(self.get_updates())
        self.session = ClientSession(connector=TCPConnector(ssl=False))

    async def stop(self):
        await self.get_updates_task
        if self.connection:
            await self.connection.close()

    async def get_updates(self):  # listener/awaiter for messages
        while True:
            await asyncio.sleep(0.5)  # for delay
            await self.queue_incoming_updates.consume(self.handle_updates)

    async def add_to_queue(self, message: Message):
        body = json.dumps(asdict(message))

        correlation_id = str(uuid.uuid4())
        reply_to_queue = await self.channel.declare_queue(exclusive=True)
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=body.encode(),
                correlation_id=correlation_id,
                reply_to=reply_to_queue.name,
            ),
            routing_key="outcoming_messages",
        )

        async with reply_to_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    if message.correlation_id == correlation_id:
                        response_data = message.body.decode()
                        response_data = json.loads(response_data)
                        try:
                            if response_data["result"] != "True":
                                chat_id = response_data["result"]["chat"]["id"]
                                if (
                                    chat_id in self.last_inline
                                ):  # we have last_inline in this chat -> delete it
                                    await self.add_to_queue(
                                        MessageToDelete(
                                            **self.last_inline[chat_id]
                                        )
                                    )
                                    self.last_inline.pop(chat_id)

                                if "reply_markup" in response_data["result"]:
                                    message_id = response_data["result"][
                                        "message_id"
                                    ]
                                    self.last_inline[chat_id] = {
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                    }
                        except KeyError:
                            pass
                        except TypeError:
                            pass
                        return response_data

    async def send_inline_create_game_and_show_scores(
        self, chat_id: int
    ) -> Message:
        inline_kb = [
            [
                {"text": "Создать новую игру", "callback_data": "create_game"},
            ],
            [
                {
                    "text": "Результаты последней игры",
                    "callback_data": "get_last_game",
                },
                {
                    "text": "Правила",
                    "callback_data": "show_rules",
                },
            ],
        ]
        kb_markup = {"inline_keyboard": inline_kb}
        return Message(
            chat_id=chat_id,
            text="Посмотреть результаты последней игры, или начать новую игру?",
            # text="Please, read the rules before start new game. Do you want to create new game or show the results of the last game in your group?",
            reply_markup=kb_markup,
        )

    async def send_inline_join_game_start_game(self, chat_id: int) -> Message:
        inline_kb = [
            [
                {"text": "Присоединиться", "callback_data": "join_game"},
                {"text": "Начать игру", "callback_data": "start_game"},
            ]
        ]
        kb_markup = {"inline_keyboard": inline_kb}

        return Message(
            chat_id=chat_id,
            text="Присоединитесь к текущей игре или начните новую игру. Необходимо как минимум 2 игрока для игровой партии.",
            # text="Please Join or Start the Game. You need minimum 2 players to start the game.",
            reply_markup=kb_markup,
        )

    async def send_inline_continue_finish_game(self, chat_id: int) -> Message:
        inline_kb = [
            [
                {"text": "Закончить", "callback_data": "finish_game"},
                {"text": "Продолжить", "callback_data": "start_game"},
            ]
        ]
        kb_markup = {"inline_keyboard": inline_kb}

        return Message(
            chat_id=chat_id,
            text="Обнаружена незаконченная игра. Хотите продолжить ее, или начать новую?",
            # text="There is unfinished game. Do you want to finish it or continue?",
            reply_markup=kb_markup,
        )

    async def send_inline_game_round_finish_game(self, chat_id: int) -> Message:
        inline_kb = [
            [
                {"text": "Закончить", "callback_data": "finish_game"},
                {"text": "Продолжить", "callback_data": "start_game"},
            ]
        ]
        kb_markup = {"inline_keyboard": inline_kb}

        return Message(
            chat_id=chat_id,
            text="Закончить игру досрочно или продолжить?",
            reply_markup=kb_markup,
        )

    async def send_photos_and_inline(
        self, chat_id: int, player_1: Player, player_2: Player
    ) -> bool:
        """
        player_1 can be blank, player_2 cannot
        if user id !=0:
            send media group, send 2 buttons
            return True - means battle between 2 players
        else:
        return False - autowin against kitty
        """
        await self.add_to_queue(
            MessageMediaGroup(
                chat_id=chat_id,
                media=[
                    {"type": "photo", "media": f"{player_1.photo_file_id}"},
                    {"type": "photo", "media": f"{player_2.photo_file_id}"},
                ],
            )
        )
        await asyncio.sleep(1)
        if player_1.id != 0:
            inline_kb = [
                [
                    {"text": "Игрок 1 (слева)", "callback_data": "voted_for_1"},
                    {
                        "text": "Игрок 2 (справа)",
                        "callback_data": "voted_for_2",
                    },
                ]
            ]
            kb_markup = {"inline_keyboard": inline_kb}
            await self.add_to_queue(
                Message(
                    chat_id=chat_id,
                    text=f"🗳️Проголосуйте за одного из участников.\n⏳Время для голосования - {VOTING_TIMER} секунд",
                    reply_markup=kb_markup,
                )
            )
            return True  # battle took place
        else:
            return None  # no voting, blank player

    async def handle_callback_query(self, chat_id: int, callback_query: Update):
        """
        return message in dependence of callback_query.data
        """

        selected_option = callback_query.object.data

        current_game = await self.make_request(
            route="get_current_game", params={"chat_id": chat_id}
        )
        current_status = await self.make_request(
            route="get_current_game_status", params={"chat_id": chat_id}
        )
        active_players = await self.make_request(
            route="get_current_game_state", params={"chat_id": chat_id}
        )
        if active_players:
            active_players = [Player(**pl) for pl in active_players]

        current_player = Player(
            id=callback_query.object.user.id,
            username=callback_query.object.user.username,
            photo_file_id="0",
        )
        if selected_option.startswith("voted_for_"):
            await self.handle_callback_query_voting(chat_id, callback_query)

        elif (
            selected_option == "create_game"
        ):  # -> send_inline_join_game_start_game OR send_inline_continue_finish_game
            """
            check if current_game in this chat, if yes - game_round/start_game
            else - create_game and send_inline_join_game_start_game
            """
            if not current_game:
                new_game = await self.make_request(
                    route="create_game", params={"chat_id": chat_id}
                )
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text="Игра создана. Необходимо минимум 2 игрока, чтобы начать игру.",
                        # text="Your game is created. Need minimum 2 players to start the game.",
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_join_game_start_game(chat_id)
                )
            else:
                await self.add_to_queue(
                    await self.send_inline_continue_finish_game(chat_id)
                )
            await self.add_to_queue(
                MessageAnswerCallback(
                    callback_query_id=callback_query.object.callback_query_id,
                )
            )

        elif (
            selected_option == "join_game"
        ):  # -> send_inline_join_game_start_game
            """
            check game status, can join only to CREATED game
            try to join player to game (if no db player record - create it, inside join_game())
            if player == None - error during join player (or add record), player must have profile photos
                else: msg with successfull join and send_inline_join_game_start_game
            """
            is_participant = await self.make_request(
                route="is_participant",
                params={"chat_id": chat_id, "player": asdict(current_player)},
            )

            if not current_game:
                await self.add_to_queue(
                    MessageAnswerCallback(
                        text=f"Сначала необходимо создать игру, прежде чем присоединиться к ней.",
                        # text=f"You need to create game, before joined it.",
                        callback_query_id=callback_query.object.callback_query_id,
                        show_alert=False,
                    )
                )
                return None

            elif is_participant:
                await self.add_to_queue(
                    MessageAnswerCallback(
                        text=f"Вы уже присоединились к этой игре💃",
                        # text=f"You've already joined this game.",
                        callback_query_id=callback_query.object.callback_query_id,
                        show_alert=False,
                    )
                )
                return None

            elif current_status != "CREATED":
                await self.add_to_queue(
                    MessageAnswerCallback(
                        text=f"🚫 Невозможно присоединиться к уже запущенной игре 🚫",
                        # text=f"You can't join started game.",
                        callback_query_id=callback_query.object.callback_query_id,
                        show_alert=False,
                    )
                )
                return None

            elif current_status == "CREATED":
                # start getting user avatar via correlation_id and replying queue
                correlation_id = str(uuid.uuid4())
                reply_to_queue = await self.channel.declare_queue(
                    exclusive=True,
                )
                message = json.dumps(
                    asdict(GetUserAvatar(user_id=current_player.id))
                )
                await self.channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message.encode(),
                        correlation_id=correlation_id,
                        reply_to=reply_to_queue.name,
                    ),
                    routing_key="outcoming_messages",
                )

                async with reply_to_queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        if message.correlation_id == correlation_id:
                            player_photo_file_id = message.body.decode().strip(
                                '"'
                            )
                            break

                new_player = Player(
                    id=current_player.id,
                    username=current_player.username,
                    photo_file_id=player_photo_file_id,
                )
                player = await self.make_request(
                    route="join_game",
                    params={"chat_id": chat_id, "player": asdict(new_player)},
                )

                if not player:
                    await self.add_to_queue(
                        MessageAnswerCallback(
                            text=f"Только пользователи с фото в профиле могут стать игроками 👻. Пожалуйста добавьте фотографию профиля или изменить настройки приватности и попробуйте еще раз.",
                            # text=f"Only users with profile photos can attend photo battle. Please add profile photo or change privacy settings and try again.",
                            callback_query_id=callback_query.object.callback_query_id,
                            show_alert=True,
                        )
                    )
                else:
                    await self.add_to_queue(
                        Message(
                            chat_id=chat_id,
                            text=f"Новый игрок - {player['username']}.\nУдачи!🍀",
                            # text=f"New player - {player.username}. Good Luck!",
                        )
                    )
                    await self.add_to_queue(
                        await self.send_inline_join_game_start_game(chat_id)
                    )

                return None
            else:
                return None

        elif (
            selected_option == "get_last_game"
        ):  # -> send_inline_create_game_and_show_scores
            """
            can only be called before game is running
            return GameResult of your last game in this chat
            """
            last_game = await self.make_request(
                route="get_last_game", params={"chat_id": chat_id}
            )

            if last_game:
                participants = ", ".join(
                    [pl["username"] for pl in last_game["players"]]
                )
                if last_game["winner"]:
                    winner = last_game["winner"]["username"]
                else:
                    winner = "Нет победителя."

                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"☑️Результаты последней игры:\n📋Участники: {participants}\n🏆Победитель: {winner}",
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_create_game_and_show_scores(chat_id)
                )

            else:
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"❌ Игры не найдены.",
                    )
                )

        elif selected_option == "start_game":  # -> game_round OR finish_game
            """
            check status and count_players, return None if any errors
            call game_round() or finish the game
            """

            if active_players:
                count_players = len(active_players)
            else:
                await self.add_to_queue(
                    MessageAnswerCallback(
                        text=f"Необходимо минимум 2 участника для игры.",
                        # text=f"Need at least 2 players for play.",
                        callback_query_id=callback_query.object.callback_query_id,
                        show_alert=False,
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_join_game_start_game(chat_id)
                )
                return None

            if current_status == "CREATED" and count_players < 2:
                await self.add_to_queue(
                    MessageAnswerCallback(
                        text=f"Необходимо минимум 2 участника для игры.",
                        # text=f"You're gorgeous without a doubt, but you can't play solo. Need at least 2 players.",
                        callback_query_id=callback_query.object.callback_query_id,
                        show_alert=True,
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_join_game_start_game(chat_id)
                )
                return None

            elif current_status == "STARTED":  #
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"Продолжаем!🚀\nУчастники этого раунда: {', '.join([pl.username for pl in active_players])}",
                        # text=f"Let's move on!",
                    )
                )

            elif current_status == "CREATED":
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"Ваша игра создана! Участвуют: {', '.join([pl.username for pl in active_players])}",
                    )
                )
                await self.make_request(
                    route="start_game", params={"chat_id": chat_id}
                )

                await self.add_to_queue(
                    await self.send_inline_join_game_start_game(chat_id)
                )

            elif current_status == "FINISHED":
                return None

            if count_players > 1:
                await self.game_round(chat_id=chat_id, players=active_players)
                await self.add_to_queue(
                    await self.send_inline_game_round_finish_game(chat_id)
                )

            elif count_players == 1:
                winner = await self.make_request(
                    route="finish_game",
                    params={
                        "chat_id": chat_id,
                        "winner": asdict(active_players[0]),
                    },
                )

                await self.add_to_queue(
                    MessagePhoto(
                        chat_id=chat_id,
                        photo=winner["photo_file_id"],
                        caption=f"Игра окончена.\nИ победителем становится... {winner['username']}!",
                        # caption=f"Game is over!\nThe winner is... {winner.username}",
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_create_game_and_show_scores(chat_id)
                )

            elif count_players == 0:
                await self.make_request(
                    route="finish_game", params={"chat_id": chat_id}
                )
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"🚫 Игра окончена без выявления победителя",
                        # text=f"Game is over! No winner this time.",
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_create_game_and_show_scores(chat_id)
                )

        elif (
            selected_option == "finish_game"
        ):  # -> send_inline_create_game_and_show_scores
            """
            call finish_game(chat_id) method. If called - meaned that game finished w/o winner
            """
            if current_game and current_status != "FINISHED":
                await self.make_request(
                    route="finish_game", params={"chat_id": chat_id}
                )
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"🚫 Игра окончена без выявления победителя",
                        # text=f"Your game is over. No winner this time.",
                    )
                )
                await self.add_to_queue(
                    await self.send_inline_create_game_and_show_scores(chat_id)
                )
            else:
                await self.add_to_queue(
                    MessageAnswerCallback(
                        text=f"❌ Вы не можете закончить не начатую игру",
                        # text=f"You can't finish unstarted game.",
                        callback_query_id=callback_query.object.callback_query_id,
                        show_alert=True,
                    )
                )
                return None

        elif (
            selected_option == "show_rules"
        ):  # -> send_inline_create_game_and_show_scores
            """
            return text message with rules
            """
            await self.add_to_queue(
                Message(
                    chat_id=chat_id,
                    text=f"Правила очень простые. Конкурс проходит по 'олимпийской турнирной системе'. Каждый раунд вам будет предложено несколько пар аватарок."
                    "В каждой паре необходимо проголосовать за одну из них в течение отведенного времени, руководствуясь своим субъективным мнением, конечно же."
                    "\Участник, набравший большее количество голосов проходит в следующий раунд. Итак до тех пор, пока не определится победитель.",
                )
            )
            await self.add_to_queue(
                await self.send_inline_create_game_and_show_scores(chat_id)
            )

        # answer for callback
        await self.add_to_queue(
            MessageAnswerCallback(
                callback_query_id=callback_query.object.callback_query_id,
            )
        )

        return None

    async def handle_callback_query_voting(
        self, chat_id: int, callback_query: Update
    ):
        """
        called when voting is active. Check if user already voted -> return alert to him
        if user not in voted - count his voice, add him to voted_players -> return alert ok
        """
        selected_option = callback_query.object.data
        voting_player = callback_query.object.user.id

        if not chat_id in self.votings or not selected_option.startswith(
            "voted_for_"
        ):
            await self.add_to_queue(
                MessageAnswerCallback(
                    text=f"Ошибка. Неверное действие.",
                    # text=f"Error. Invalid action.",
                    callback_query_id=callback_query.object.callback_query_id,
                    show_alert=False,
                )
            )
            return None

        if voting_player in self.votings[chat_id]["voted_players"]:
            await self.add_to_queue(
                MessageAnswerCallback(
                    text=f"Вы уже проголосовали в этом раунде.",
                    # text=f"You have already voted in this round.",
                    callback_query_id=callback_query.object.callback_query_id,
                    show_alert=True,
                )
            )
        else:
            if selected_option == "voted_for_1":
                self.votings[chat_id]["counter"] -= 1
            elif selected_option == "voted_for_2":
                self.votings[chat_id]["counter"] += 1

            self.votings[chat_id]["voted_players"].append(voting_player)
            await self.add_to_queue(
                MessageAnswerCallback(
                    text=f"Спасибо за ваш голос!",
                    # text=f"Thanks for your vote!",
                    callback_query_id=callback_query.object.callback_query_id,
                    show_alert=True,
                )
            )

    async def game_round(
        self, chat_id, players: list[Player]
    ):  # send_inline_continue_finish_game
        """
        accept list of Players (status != 0)
        - check len of players, it must be 2**
              add "blank" players (max=len/2 -1) they never meet each other in round
        set random pairs, start voting:
        - add chat_id to self.votings - block all other activities

        cycle for pairs:
            cycle: pop 2 randoms from list, if any "blank" players -
                   they paired with random not "blank" and automatically lose
                   if not blanks in pair: add record to self.voting and async wait VOTING_TIMER seconds
                                          handle click on voting buttons via handle_callback_query_voting
                                          after - received result from self.voting[chat_id]
                   else:
                   pop self.voting[chat_id]
                   send_message with player winner
                   call set_winner_and_loser(chat_id, winner, loser)
        """
        players_count = len(players)
        assert players_count > 1
        for i in range(1, 5):  # assuming max players number = 2**4=16
            active_players_count = pow(2, i)  # number of players for round
            if active_players_count >= players_count:
                break
        blanks_count = active_players_count - players_count
        assert active_players_count / 2 - 1 >= blanks_count >= 0
        number_of_pairs = active_players_count // 2
        cat_phrases = [
            "Ну привет",
            "Голосуй за меня!",
            "Я самый лучшайший!",
            "Мурмяяяяу",
            "Наташа, неси еду",
            "Дратути",
            "Я выше всего этого",
        ]

        for _ in range(number_of_pairs):
            if blanks_count > 0:
                cat_says = cat_phrases.pop(
                    random.randint(0, len(cat_phrases) - 1)
                )
                player_1 = Player(
                    id=0,
                    username=None,
                    photo_file_id=f"https://cataas.com/cat/says/{cat_says}",
                )
                player_2 = players.pop(random.randint(0, len(players) - 1))
                blanks_count -= 1
            else:
                player_1 = players.pop(random.randint(0, len(players) - 1))
                player_2 = players.pop(random.randint(0, len(players) - 1))

            pair = [player_1, player_2]
            await self.add_to_queue(
                Message(
                    chat_id=chat_id,
                    text=f"⚔️ Начинаем следующую битву аватарок! ⚔️\nГолосование начинается...",
                    # text=f"Prepare for the next battle!",
                )
            )
            # BATTLE BEGINS!
            await asyncio.sleep(3)
            success_battle = await self.send_photos_and_inline(
                chat_id, player_1, player_2
            )

            if success_battle:  # player VS player
                self.votings[chat_id] = {
                    "voted_players": [],
                    "counter": 0,
                }
                await asyncio.sleep(VOTING_TIMER)

                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text="Битва окончена. Считаю голоса 🗳️ ...",
                        # text="Battle is over. Counting votes.",
                    )
                )
                await asyncio.sleep(3)  # sleep to not send messages immediately

                if self.votings[chat_id]["counter"] < 0:
                    winner = player_1
                    loser = player_2
                    win_txt = (
                        f"В следующий тур проходит... {player_1.username}!"
                    )
                elif self.votings[chat_id]["counter"] > 0:
                    winner = player_2
                    loser = player_1
                    win_txt = (
                        f"В следующий тур проходит... {player_2.username}!"
                    )
                else:  # = 0
                    winner = pair.pop(random.randint(0, 1))
                    assert len(pair) == 1
                    loser = pair[0]
                    win_txt = f"Оба участника набрали равное число голосов.\n🎲 И бог рандома выбирает... {winner.username}!"
                    # win_txt = f"Each player received the same number of votes.\nAnd God of random choose... {winner.username}!"
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=win_txt,
                    )
                )
                self.votings.pop(chat_id)  # end voting

            else:  # auto-win against kitty
                await asyncio.sleep(3)
                winner = player_2
                loser = None
                await self.add_to_queue(
                    Message(
                        chat_id=chat_id,
                        text=f"Игрок 1 был дисквалифицирован, потому что у него лапки 🐾! Мы пока разбираемся, как кот сумел пройти через нашу систему регистрации.\nА в следующий тур проходит... {player_2.username}!",
                        # text=f"Player 1 was disqualified because he has paws!\nCongratulations to {player_2.username}!",
                    )
                )
                await asyncio.sleep(5)

            if loser:
                await self.make_request(
                    route="set_winner_and_loser",
                    params={
                        "chat_id": chat_id,
                        "winner": asdict(winner),
                        "loser": asdict(loser),
                    },
                )
            else:
                await self.make_request(
                    route="set_winner_and_loser",
                    params={
                        "chat_id": chat_id,
                        "winner": asdict(winner),
                    },
                )

    async def make_request(self, route: str, params: Optional[dict]):
        '''
        additional method to make API requests to DB
        '''
        data = json.dumps(params)
        async with self.session.post(
            url=f"http://web:8080/{route}",
            data=data,
            headers={"Content-Type": "application/json"},
        ) as response:
            results = await response.json()

            result_return = {
                "create_game": "chat_id",
                "join_game": "player",
                "is_participant": "is_participant",
                "get_current_game": "current_game_id",
                "get_current_game_state": "active_players",
                "get_current_game_status": "current_game_status",
                "start_game": "start_game",
                "get_last_game": "last_game",
                "finish_game": "winner",
                "set_winner_and_loser": "set_winner_and_loser",
            }
            if results["status"] == "ok":
                data = results["data"]
                return data[result_return[route]]
            else:
                return None

    @staticmethod
    def to_update_dataclass(update: dict) -> Update | None:
        try:
            if "message" in update:
                update_type = "message"
                upd_obj = UpdateObject(
                    id=update["message"]["message_id"],
                    user=Player(
                        id=update["message"]["from"]["id"],
                        username=update["message"]["from"]["username"],
                    ),
                    chat_id=update["message"]["chat"]["id"],
                    text=update["message"]["text"],
                )

            elif "callback_query" in update:
                update_type = "callback_query"
                upd_obj = UpdateObject(
                    id=update["callback_query"]["message"]["message_id"],
                    user=Player(
                        id=update["callback_query"]["from"]["id"],
                        username=update["callback_query"]["from"]["username"],
                    ),
                    chat_id=update["callback_query"]["message"]["chat"]["id"],
                    text=update["callback_query"]["message"]["text"],
                    data=update["callback_query"]["data"],
                    callback_query_id=update["callback_query"]["id"],
                )
        except KeyError:
            return None
        return Update(id=update["update_id"], type=update_type, object=upd_obj)

    async def handle_updates(self, incoming_update: aio_pika.IncomingMessage):
        async with incoming_update.process(ignore_processed=True):
            body = incoming_update.body.decode()
            up_json = json.loads(body)
            update = self.to_update_dataclass(up_json)

            if not update:
                return None

            chat_id = update.object.chat_id
            update_type = update.type

            if (
                chat_id in self.votings
            ):  # it's voting time! block everything except callbacks voting
                if update_type == "callback_query":
                    asyncio.create_task(
                        self.handle_callback_query_voting(chat_id, update)
                    )

            elif update_type == "message" and update.object.text.startswith(
                "/start"
            ):
                message = Message(
                    chat_id=chat_id,
                    text="Привет 👋! Я PhotoBattle бот!\nПожалуйста, ознакомьтесь с правилами прежде чем начать игру.",
                )
                await self.add_to_queue(message)
                await self.add_to_queue(
                    await self.send_inline_create_game_and_show_scores(chat_id)
                )

            elif update_type == "callback_query":
                asyncio.create_task(self.handle_callback_query(chat_id, update))

            # ECHO BOT
            # elif update_type == "message":
            #     message = Message(
            #         chat_id=chat_id,
            #         text=update.object.text,
            #     )
            #     await self.add_to_queue(message)
            # else:
            #     pass

            await incoming_update.ack()


async def main():
    manager = Manager()
    task = asyncio.create_task(manager.start())

    try:
        await task
    except asyncio.CancelledError:
        print("Main task stopped")
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
