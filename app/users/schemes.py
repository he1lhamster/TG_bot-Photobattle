from marshmallow import Schema, fields


class PlayerSchema(Schema):
    id = fields.Int(required=False)
    username = fields.Str(required=False)
    photo_file_id = fields.Str(required=False)


class AdminSchema(Schema):
    id = fields.Int(required=False)
    email = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)
