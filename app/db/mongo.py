import motor.motor_asyncio
import app.config as settings

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None


def get_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]


def get_sources_col():
    return get_db()["knowledge_sources"]


def get_bm25_col():
    return get_db()["knowledge_bm25_global"]
