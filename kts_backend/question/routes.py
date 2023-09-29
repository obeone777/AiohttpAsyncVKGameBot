import typing

from kts_backend.question.views import QuestionAddView

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/add_question", QuestionAddView)
