from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from urllib.parse import urlparse
from app.config import settings


raw_url = settings.database_url

# Convert postgres:// / postgresql:// to postgresql+asyncpg:// for async driver
if raw_url.startswith("postgresql://"):
    engine_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgres://"):
    engine_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    engine_url = raw_url

engine_url = engine_url.replace("?sslmode=require", "").replace("&sslmode=require", "")

# SSL for Supabase (asyncpg)
connect_args: dict = {"ssl": "require"}

# Transaction pooler (port 6543) — disable prepared statement cache
parsed = urlparse(raw_url)
if parsed.port == 6543:
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0

engine = create_async_engine(engine_url, connect_args=connect_args, echo=False)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
