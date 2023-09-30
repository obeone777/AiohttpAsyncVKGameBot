from aiohttp.web_app import Application


def setup_routes(app: Application):
    from kts_backend.admin.routes import setup_routes as admin_setup_routes
    from kts_backend.game.routes import setup_routes as game_setup_routes
    from kts_backend.question.routes import setup_routes as question_setup_routes

    admin_setup_routes(app)
    game_setup_routes(app)
    question_setup_routes(app)
