from aiohttp_apispec import request_schema, response_schema
from aiohttp_session import new_session, get_session
from aiohttp.web import (
    HTTPForbidden,
    HTTPUnauthorized,
    HTTPMethodNotAllowed,
    HTTPBadRequest,
)
from users.schemes import AdminSchema, PlayerSchema
from web.app import View
from web.utils import json_response
from web.mixins import AuthRequiredMixin
from hashlib import sha256


class AdminLoginView(View):
    @request_schema(AdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        data = self.request["data"]
        email = data["email"]
        password = data["password"]
        admin = await self.request.app.store.user.get_admin_by_email(email)

        if admin:
            if admin.is_password_valid(password):
                session = await new_session(request=self.request)
                session["admin"] = {"id": admin.id, "email": admin.email}
                return json_response(
                    data={"id": admin.id, "email": admin.email}
                )
            else:
                raise HTTPForbidden
        else:
            raise HTTPForbidden

    async def get(self):
        raise HTTPMethodNotAllowed(
            method=self.request.method, allowed_methods=["POST"]
        )


class AdminCurrentView(AuthRequiredMixin, View):
    @response_schema(AdminSchema, 200)
    async def get(self):
        session = await get_session(request=self.request)
        try:
            admin = await self.request.app.store.user.get_admin_by_email(
                session["admin"]["email"]
            )
            if admin:
                return json_response(
                    data={"id": admin.id, "email": admin.email}
                )
            else:
                raise HTTPUnauthorized
        except KeyError:
            raise HTTPUnauthorized


class DeletePlayerView(AuthRequiredMixin, View):
    @request_schema(PlayerSchema)
    @response_schema(PlayerSchema, 200)
    async def post(self):
        data = self.request["data"]
        user_id = data["id"]

        player = await self.request.app.store.user.get_user_by_id(user_id)
        if player:
            await self.request.app.store.user.delete_player_by_id(user_id)
            return json_response(data={"removed": PlayerSchema().dump(player)})
        else:
            raise HTTPBadRequest
