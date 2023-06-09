"""init migr

Revision ID: bc46f3ae9ac9
Revises: 
Create Date: 2023-03-28 18:38:49.891287

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bc46f3ae9ac9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("CREATED", "STARTED", "FINISHED", name="status"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("photo_file_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "gamescores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=True),
        sa.Column("player_id", sa.BigInteger(), nullable=True),
        sa.Column("player_status", sa.Integer(), nullable=True),
        sa.Column("game_round", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("gamescores")
    op.drop_table("players")
    op.drop_table("games")
    op.drop_table("admins")
    # ### end Alembic commands ###
