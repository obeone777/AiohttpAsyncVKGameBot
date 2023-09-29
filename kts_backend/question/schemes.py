from marshmallow import fields, Schema


class QuestionSchema(Schema):
    id = fields.Int(required=False)
    question_text = fields.Str(required=True)
    answer_text = fields.Str(required=True)
