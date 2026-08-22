from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import pathlib
from dotenv import load_dotenv

env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Fallback to local sqlite if no DATABASE_URL is provided
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./olrac_signage.db")

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import redis.asyncio as redis_async
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_pool = redis_async.ConnectionPool.from_url(REDIS_URL)

def get_redis():
    return redis_async.Redis(connection_pool=redis_pool)

# arq parses the DSN itself, so credentials, TLS (rediss://) and the database index all
# survive. The hand-rolled split() this replaces understood only "redis://host:port/db",
# which is the one shape no managed provider hands out:
#
#   redis://default:pw@host:6379   -> ValueError: int("pw@host") -- crashed at IMPORT, so
#                                     the whole API failed to boot.
#   rediss://default:pw@host:6379  -> did not match "redis://", fell through to
#                                     RedisSettings() = localhost:6379. Worse than the
#                                     crash: the app started, the queue looked healthy,
#                                     and no job ever ran.
REDIS_SETTINGS = RedisSettings.from_dsn(REDIS_URL)
