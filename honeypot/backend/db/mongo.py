from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect_db():
    global _client
    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=100,
        minPoolSize=10,
        serverSelectionTimeoutMS=5000,
    )
    logger.info("MongoDB connected")


async def close_db():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_db():
    return _client[settings.MONGODB_DATABASE]


def get_collection(name: str):
    return get_db()[name]


class DatabaseProxy:
    def __getattr__(self, name):
        if _client is None:
            raise RuntimeError("MongoDB not initialized. Check logs for connection errors.")
        return getattr(get_db(), name)


db = DatabaseProxy()
