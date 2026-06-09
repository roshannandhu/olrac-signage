import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from sqlalchemy import text

url = settings.database_url
if url.startswith('postgresql://'):
    url = url.replace('postgresql://', 'postgresql+asyncpg://', 1)
url = url.replace('?sslmode=require', '').replace('&sslmode=require', '')

engine = create_async_engine(url, connect_args={'ssl': 'require', 'statement_cache_size': 0, 'prepared_statement_cache_size': 0})

async def setup():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE POLICY \"Public Access media\" ON storage.objects FOR ALL USING (bucket_id = 'media');"))
        print('Policy created')
    await engine.dispose()

asyncio.run(setup())
