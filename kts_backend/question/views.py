from aiohttp_apispec import docs, request_schema, response_schema
from sqlalchemy.exc import IntegrityError
from kts_backend.question.mixins import AuthRequiredMixin
from kts_backend.question.schemes import QuestionSchema
from kts_backend.web.app import View
from kts_backend.web.utils import json_response


class QuestionAddView(AuthRequiredMixin, View):
    @docs(tags=["Question"], summary="Add question")
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema, 200)
    async def post(self):
        question = self.data["question_text"]
        answer = self.data["answer_text"]
        try:
            question_answer = await self.store.question.create_question(
                question, answer
            )
            return json_response(data=QuestionSchema().dump(question_answer))
        except IntegrityError as e:
            raise f'Произошла ошибка: {e}'
