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
import warnings
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_pool = redis_async.ConnectionPool.from_url(REDIS_URL)

def get_redis():
    return redis_async.Redis(connection_pool=redis_pool)

if REDIS_URL.startswith("redis://"):
    parts = REDIS_URL.split("://")[1].split("/")
    host_port = parts[0].split(":")
    redis_host = host_port[0]
    redis_port = int(host_port[1]) if len(host_port) > 1 else 6379
    redis_db = int(parts[1]) if len(parts) > 1 else 0
    REDIS_SETTINGS = RedisSettings(host=redis_host, port=redis_port, database=redis_db)
else:
    REDIS_SETTINGS = RedisSettings()
