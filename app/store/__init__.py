import typing
import asyncio
from store.database.database import Database

if typing.TYPE_CHECKING:
    from web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from users.accessor import UserAccessor

        # from store.bot.manager import BotManager
        from store.game.accessor import GameAcessor

        self.user = UserAccessor(app)
        # self.bots_manager = BotManager(app)
        self.game = GameAcessor(app)


# async def start_manager(bot_manager):
#     await bot_manager.start()


def setup_store(app: "Application"):
    app.database = Database(app)
    app.store = Store(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    # app.on_cleanup.append(app.store.bots_manager.stop)

    # asyncio.run(start_manager(app.store.bots_manager))
