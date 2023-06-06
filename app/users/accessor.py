import typing

from base.base_accessor import BaseAccessor
from users.models import PlayerModel, Player, Admin, AdminModel
from typing import Optional
from sqlalchemy import select, delete, func
from hashlib import sha256


class UserAccessor(BaseAccessor):
    async def create_user(self, user: Player) -> Optional[Player]:
        async with self.app.database.session.begin() as Session:
            new_player = PlayerModel(
                id=user.id,
                username=user.username,
                photo_file_id=user.photo_file_id,
            )
            Session.add(new_player)
            await Session.commit()
            return user

    async def get_user_by_id(self, player_id: int) -> Optional[Player]:
        async with self.app.database.session.begin() as Session:
            player = await Session.execute(
                select(
                    PlayerModel.id,
                    PlayerModel.username,
                    PlayerModel.photo_file_id,
                ).where(PlayerModel.id == player_id)
            )
            player = player.mappings().fetchone()

            if player:
                return Player(
                    id=player["id"],
                    username=player["username"],
                    photo_file_id=player["photo_file_id"],
                )
            else:
                return None

    async def delete_player_by_id(self, player_id):
        async with self.app.database.session.begin() as Session:
            # await Session.execute(
            #     text(f"delete from players where id={player_id};")
            # )
            await Session.execute(
                delete(PlayerModel).where(PlayerModel.id == player_id)
            )
            await Session.commit()

    async def get_admin_by_email(self, email: str) -> Admin | None:
        async with self.app.database.session.begin() as Session:
            # first_admin = await Session.execute(
            #     text("select count(1) from admins")
            # )
            first_admin = await Session.execute(
                select(func.count(AdminModel.id))
            )
            first_admin = first_admin.mappings().fetchone()["count"]
            if not first_admin:
                new_admin = AdminModel(
                    email=self.app.config.admin.email,
                    password=sha256(
                        str.encode(self.app.config.admin.password)
                    ).hexdigest(),
                )
                Session.add(new_admin)

            # admin = await Session.execute(
            #     text(f"select * from admins where email='{email}'")
            # )
            admin = await Session.execute(
                select(AdminModel).where(AdminModel.email == email)
            )
            admin = admin.mappings().fetchone()
            await Session.commit()
            if admin:
                return Admin(
                    id=admin["id"],
                    email=admin["email"],
                    password=admin["password"],
                )
            else:
                return None

    async def create_admin(self, email: str, password: str) -> Admin:
        async with self.app.database.session.begin() as Session:
            admin = await self.get_admin_by_email(email)
            if not admin:
                admin = AdminModel(
                    email=email,
                    password=sha256(str.encode(password)).hexdigest(),
                )
                Session.add(admin)
                await Session.commit()

            return admin
