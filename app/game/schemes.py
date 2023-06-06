from marshmallow import Schema, fields


class GameResultSchema(Schema):
    game_id = fields.Int(required=True)
    chat_id = fields.Int(required=True)
    winner = fields.Nested("PlayerSchema", required=False)
    players = fields.Nested("PlayerSchema", many=True, required=True)


class GameSchema(Schema):
    id = fields.Int(required=False)
    chat_id = fields.Int(required=False)
    status = fields.Str(required=False)


class PlayerInGameSchema(Schema):
    chat_id = fields.Int(required=True)
    player = fields.Nested("PlayerSchema", required=True)


class IsParticipantSchema(Schema):
    is_participant: fields.Bool(required=True)
