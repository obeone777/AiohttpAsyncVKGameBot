from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def use_inspector(conn):
    inspector = inspect(conn)
    return inspector.get_table_names()


async def check_empty_table_exists(cli, tablename: str):
    engine: AsyncEngine = cli.app.database._engine
    async with engine.begin() as conn:
        tables = await conn.run_sync(use_inspector)

    assert tablename in tables
