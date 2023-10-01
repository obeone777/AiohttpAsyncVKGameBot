from marshmallow import Schema, fields


class LeaderBoardSchema(Schema):
    vk_id = fields.Int()
    name = fields.Str()
    last_name = fields.Str()
    total_points = fields.Int()
