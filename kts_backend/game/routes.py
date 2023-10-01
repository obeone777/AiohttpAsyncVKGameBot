import typing

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


def setup_routes(app: "Application"):
    from kts_backend.game.views import LeaderboardView

    app.router.add_view("/leaderboard", LeaderboardView)
