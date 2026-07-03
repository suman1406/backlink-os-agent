import asyncio
import logging
from datetime import datetime, timedelta
from app.db.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    db = await Database.get_db()
    if db is None:
        logger.error("Database connection failed.")
        return

    # Check if we already seeded
    existing_campaign = await db.campaigns.find_one({"name": "Demo Campaign"})
    if existing_campaign:
        logger.info("Database is already seeded.")
        return

    logger.info("Seeding database with demo data...")
    
    # 1. Campaigns
    campaign_id = "camp_" + str(int(datetime.utcnow().timestamp()))
    await db.campaigns.insert_one({
        "campaign_id": campaign_id,
        "name": "Demo Campaign",
        "status": "running",
        "created_at": datetime.utcnow() - timedelta(days=2),
        "target_keywords": ["b2b saas", "growth hacking"],
        "emails_sent": 142,
        "replies_received": 18,
        "meetings_booked": 3
    })

    # 2. Opportunities (CRM)
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
        },
        {
            "campaign_id": campaign_id,
            "url": "https://growthhackers.com/resources",
            "domain": "growthhackers.com",
            "fit_score": 8,
            "status": "replied",
            "contact_email": "partners@growthhackers.com",
            "discovered_at": datetime.utcnow() - timedelta(days=2),
            "last_action_at": datetime.utcnow() - timedelta(minutes=30)
        }
    ]
    await db.opportunities.insert_many(opportunities)

    # 3. Reasoning Logs
    logs = [
        {
            "campaign_id": campaign_id,
            "agent": "WebsiteAnalyzer",
            "task": "Analyze our website",
            "status": "completed",
            "duration": 2.3,
            "timestamp": datetime.utcnow() - timedelta(minutes=15)
        },
        {
            "campaign_id": campaign_id,
            "agent": "BacklinkDiscovery",
            "task": "Discover targets",
            "status": "completed",
            "duration": 1.5,
            "timestamp": datetime.utcnow() - timedelta(minutes=10)
        },
        {
            "campaign_id": campaign_id,
            "agent": "OpportunityQualification",
            "task": "Qualify target saasweekly.com",
            "status": "completed",
            "duration": 4.1,
            "timestamp": datetime.utcnow() - timedelta(minutes=5)
        }
    ]
    await db.logs.insert_many(logs)

    logger.info("Demo data seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
