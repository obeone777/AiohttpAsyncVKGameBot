from hashlib import sha256
from typing import Optional

from sqlalchemy import select

from kts_backend.admin.models import Admin
from kts_backend.base.base_accessor import BaseAccessor


class AdminAccessor(BaseAccessor):

    async def get_by_email(self, email: str) -> Optional[Admin]:
        query = select(Admin).where(Admin.email == email)
        response = await self.app.database.orm_select(query=query)
        admin = response.scalar()
        if admin:
            return admin

    async def create_admin(self, email: str, password: str) -> Admin:
        admin = Admin(email=email, password=sha256(password.encode()).hexdigest())
        await self.app.database.orm_add(admin)