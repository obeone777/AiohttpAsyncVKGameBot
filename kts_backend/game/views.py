from logging import Logger

from aiohttp_apispec import docs, response_schema

from kts_backend.game.schemes import LeaderBoardSchema
from kts_backend.web.app import View
from kts_backend.web.utils import json_response


class LeaderboardView(View):
    @docs(tags=["Game"], summary="Get Leaderboard")
    @response_schema(LeaderBoardSchema, 200)
    async def get(self):
        leaderboard = await self.store.game.get_leaderboard()
        logger = Logger("game")
        logger.info(leaderboard)
        return json_response(data=LeaderBoardSchema(many=True).dump(leaderboard))
