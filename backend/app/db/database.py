"""
Database module — single Motor (AsyncIOMotorClient) instance.

Design decisions:
- One client, created once on startup, shared globally.
- NO loop_id re-init logic — Motor handles event loop lifecycle natively.
- serverSelectionTimeoutMS=5000 so failures surface quickly.
- Structured error helper prevents raw 500s leaking internals.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
import os

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect_db(cls):
        """Initialize the Motor client. Called ONCE on app startup."""
        try:
            # Read directly from env so Docker env_file injection works
            # regardless of pydantic .env path resolution issues.
            uri = os.environ.get("MONGODB_URI", "mongodb://mongodb:27017/outreach_platform")
            # Strip surrounding quotes that bash may inject
            uri = uri.strip().strip('"').strip("'")

            logger.info(f"Connecting to MongoDB at: {uri}")
            cls.client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )

            # Extract db name from URI
            db_name = uri.rstrip("/").split("/")[-1].split("?")[0]
            if not db_name or db_name.startswith("mongodb"):
                db_name = "outreach_platform"

            cls.db = cls.client[db_name]

            # Verify connectivity with a quick ping
            await cls.client.admin.command("ping")
            logger.info(f"✓ MongoDB connected. Database: '{db_name}'")

            await cls.setup_indexes()
        except Exception as e:
            logger.error(f"✗ MongoDB connection failed: {e}")
            raise

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed.")

    @classmethod
    async def get_db(cls) -> AsyncIOMotorDatabase:
        """
        Returns the shared Motor database handle.
        If not initialized (should not happen after startup), re-initializes.
        """
        if cls.db is None:
            logger.warning("get_db() called before connect_db() — re-connecting.")
            await cls.connect_db()
        return cls.db

    @classmethod
    async def ping(cls) -> dict:
        """Returns diagnostics for the /debug/database endpoint."""
        try:
            import motor
            result = await cls.client.admin.command("ping")
            collections = await cls.db.list_collection_names()
            return {
                "status": "ok",
                "uri": os.environ.get("MONGODB_URI", "not set"),
                "db_name": cls.db.name if cls.db else None,
                "ping": result,
                "collections": collections,
                "client_type": str(type(cls.client)),
                "motor_version": motor.version,
            }
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @classmethod
    async def setup_indexes(cls):
        """Create all required indexes idempotently."""
        if cls.db is None:
            return
        logger.info("Setting up database indexes...")

        await cls.db.websites.create_index("url", unique=True)

        await cls.db.campaigns.create_index("campaign_id", unique=True)
        await cls.db.campaigns.create_index("status")
        await cls.db.campaigns.create_index("created_at")

        await cls.db.opportunities.create_index(
            [("campaign_id", 1), ("url", 1)], unique=True
        )

        await cls.db.logs.create_index("campaign_id")
        await cls.db.logs.create_index("timestamp")

        await cls.db.events.create_index(
            [("campaign_id", 1), ("sequence", 1)], unique=True
        )
        await cls.db.events.create_index("created_at")

        await cls.db.node_runs.create_index(
            [("campaign_id", 1), ("node", 1)], unique=True
        )
        await cls.db.outreach_drafts.create_index(
            [("campaign_id", 1), ("target_url", 1)], unique=True
        )

        await cls.db.crawl_cache.create_index("url", unique=True)
        await cls.db.crawl_cache.create_index("expires_at", expireAfterSeconds=0)

        logger.info("✓ Indexes ready.")


# Singleton instance used throughout the app
db = Database()
