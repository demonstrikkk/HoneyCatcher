import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import asyncio
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        """
        Connect to MongoDB with retry logic.
        """
        uri = settings.MONGO_URI
        db_name = settings.DB_NAME
        
        retries = 3
        delay = 2

        for attempt in range(retries):
            try:
                logger.info(f"Connecting to MongoDB at {uri} (Attempt {attempt + 1}/{retries})...")
                cls.client = AsyncIOMotorClient(
                    uri,
                    serverSelectionTimeoutMS=5000
                )
                # Verify connection
                await cls.client.admin.command('ping')
                cls.db = cls.client[db_name]
                logger.info("✅ Connected to MongoDB.")
                return
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"❌ MongoDB Connection failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.critical("🚨 Could not connect to MongoDB after multiple attempts.")
                    raise e

    @classmethod
    async def close(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed.")

class DatabaseProxy:
    """
    Proxy to the MongoDB database instance.
    This allows importing 'db' at module level before it's initialized.
    """
    def __getattr__(self, name):
        if MongoDB.db is None:
            raise RuntimeError("MongoDB not initialized. Check logs for connection errors.")
        return getattr(MongoDB.db, name)

# Global DB instance proxy
db = DatabaseProxy()
