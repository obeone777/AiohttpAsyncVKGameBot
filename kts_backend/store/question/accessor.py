from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.question.models import QuestionAnswer

class QuestionAccessor(BaseAccessor):
    async def create_question(self, question: str, answer: str) -> QuestionAnswer:
        question = QuestionAnswer(question_text=question, answer_text=answer)
        await self.app.database.orm_add(question)
        return question