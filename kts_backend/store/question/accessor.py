from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.question.models import Question

class QuestionAccessor(BaseAccessor):
    async def create_question(self, question: str, answer: str) -> Question:
        question = Question(question=question, answer=answer)
        await self.app.database.orm_add(question)
        return question