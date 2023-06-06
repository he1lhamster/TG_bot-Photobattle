from aiohttp.web_app import Application

import typing

from users.views import AdminLoginView, AdminCurrentView, DeletePlayerView

if typing.TYPE_CHECKING:
    from web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/admin.login", AdminLoginView)
    app.router.add_view("/admin.current", AdminCurrentView)
    app.router.add_view("/delete_player", DeletePlayerView)
