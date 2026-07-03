from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None
    loop_id: int = 0

    @classmethod
    async def connect_db(cls):
        try:
            logger.info("Connecting to MongoDB...")
            if cls.client:
                cls.client.close()
            cls.client = AsyncIOMotorClient(settings.MONGODB_URI)
            cls.loop_id = id(asyncio.get_running_loop())
            # Parse DB name from URI or fallback
            db_name = settings.MONGODB_URI.split("/")[-1].split("?")[0]
            if not db_name or db_name == settings.MONGODB_URI:
                db_name = "outreach_platform"
            cls.db = cls.client[db_name]
            logger.info(f"Connected to MongoDB database: {db_name}")
            
            await cls.setup_indexes()
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise e

    @classmethod
    async def seed_demo_data_if_empty(cls):
        if cls.db is None:
            return
        count = await cls.db.campaigns.count_documents({})
        if count == 0:
            logger.info("No campaigns found, seeding demo data...")
            import sys
            import os
            
            # Since we are in app/db/database.py, we can just run the logic here or import
            from datetime import datetime, timedelta
            
            campaign_id = "camp_" + str(int(datetime.utcnow().timestamp()))
            await cls.db.campaigns.insert_one({
                "campaign_id": campaign_id,
                "name": "Demo Campaign",
                "status": "running",
                "created_at": datetime.utcnow() - timedelta(days=2),
                "target_keywords": ["b2b saas", "growth hacking"],
                "emails_sent": 142,
                "replies_received": 18,
                "meetings_booked": 3
            })

            opportunities = [
                {
                    "campaign_id": campaign_id,
                    "url": "https://techcrunch.com/demo-article",
                    "domain": "techcrunch.com",
                    "fit_score": 9,
                    "status": "contacted",
                    "contact_email": "editor@techcrunch.com",
                    "discovered_at": datetime.utcnow() - timedelta(days=1),
                    "last_action_at": datetime.utcnow() - timedelta(hours=5)
                },
                {
                    "campaign_id": campaign_id,
                    "url": "https://saasweekly.com/guest-post",
                    "domain": "saasweekly.com",
                    "fit_score": 7,
                    "status": "qualified",
                    "contact_email": "hello@saasweekly.com",
                    "discovered_at": datetime.utcnow() - timedelta(days=2),
                    "last_action_at": datetime.utcnow() - timedelta(days=1)
                }
            ]
            await cls.db.opportunities.insert_many(opportunities)
            logger.info("Demo data seeded.")

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed.")

    @classmethod
    async def get_db(cls) -> AsyncIOMotorDatabase:
        current_loop_id = id(asyncio.get_running_loop())
        if cls.db is None or cls.loop_id != current_loop_id:
            await cls.connect_db()
        return cls.db

    @classmethod
    async def setup_indexes(cls):
        """Autonomously setup collections and indexes."""
        if cls.db is None:
            return
        logger.info("Setting up database indexes...")
        
        # websites collection
        await cls.db.websites.create_index("url", unique=True)
        
        # campaigns collection
        await cls.db.campaigns.create_index("campaign_id", unique=True)
        await cls.db.campaigns.create_index("status")
        await cls.db.campaigns.create_index("created_at")
        
        # opportunities collection
        await cls.db.opportunities.create_index([("campaign_id", 1), ("url", 1)], unique=True)
        
        # logs collection
        await cls.db.logs.create_index("campaign_id")
        await cls.db.logs.create_index("timestamp")

        # events collection powers SSE replay and exact-once frontend rendering
        await cls.db.events.create_index([("campaign_id", 1), ("sequence", 1)], unique=True)
        await cls.db.events.create_index("created_at")

        # node runs power dashboard restore and hover detail
        await cls.db.node_runs.create_index([("campaign_id", 1), ("node", 1)], unique=True)
        await cls.db.outreach_drafts.create_index([("campaign_id", 1), ("target_url", 1)], unique=True)

        # cache collection
        await cls.db.crawl_cache.create_index("url", unique=True)
        await cls.db.crawl_cache.create_index("expires_at", expireAfterSeconds=0)

db = Database()
