from sqlalchemy import select

from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.users.models import User


class UserAccessor(BaseAccessor):
    async def get_user_by_vkid(self, vkid: int) -> User:
        query = select(User).where(User.vk_id == vkid)
        user = await self.app.database.orm_select(query)
        user = user.scalar()
        self.logger.info(user)
        return User(vk_id=vkid, name=user.name, last_name=user.last_name)
