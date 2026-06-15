from contextlib import asynccontextmanager
from fastapi import FastAPI
from db.mongo import connect_db, close_db
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HoneyBadger backend...")
    await connect_db()
    yield
    await close_db()
    logger.info("Backend shutdown complete.")
