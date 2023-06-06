from aiohttp.web_app import Application


def setup_routes(app: Application):
    from users.routes import setup_routes as users_setup_routes
    from game.routes import setup_routes as game_setup_routes

    users_setup_routes(app)
    game_setup_routes(app)
