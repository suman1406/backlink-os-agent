import logging
import asyncio
from typing import Dict, Any, Optional
from firecrawl import FirecrawlApp
from app.core.config import settings
from app.db.database import Database
from app.core.resilience import CircuitBreaker, AsyncRateLimiter, retry_async
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CrawlerProvider:
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.app = FirecrawlApp(api_key=self.api_key) if self.api_key else None
        self.breaker = CircuitBreaker()
        self.rate_limiter = AsyncRateLimiter(max_calls=20, window_seconds=60)
        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY is not set. Crawler will use deterministic fallback content.")

    async def crawl(self, url: str) -> Dict[str, Any]:
        logger.info(f"Crawling URL: {url}")
        
        # Check cache in DB
        db = await Database.get_db()
        cached = await db.crawl_cache.find_one({"url": url, "expires_at": {"$gt": datetime.utcnow()}})
        if cached:
            logger.info(f"Cache hit for {url}")
            return {"markdown": cached.get("markdown", ""), "provider": "Firecrawl cache", "cached": True}

        if not self.app:
            return {
                "markdown": f"Fallback crawl summary for {url}. Provider credentials are unavailable.",
                "provider": "crawler-fallback",
                "cached": False,
                "degraded": True,
            }

        try:
            await self.rate_limiter.acquire()

            # Fallback to default scrape_url arguments to prevent TypeError in this SDK version
            async def scrape():
                def call_firecrawl():
                    try:
                        return self.app.scrape_url(url, params={'formats': ['markdown']})
                    except TypeError:
                        return self.app.scrape_url(url)

                return await asyncio.to_thread(call_firecrawl)

            response = await retry_async(scrape, attempts=2, timeout=25.0, breaker=self.breaker)
            
            # Handle Pydantic Document object from Firecrawl
            if hasattr(response, 'markdown'):
                markdown = response.markdown
            elif isinstance(response, dict):
                markdown = response.get("markdown", "")
            else:
                # Try to convert to dict if it's a model
                try:
                    response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.dict()
                    markdown = response_dict.get("markdown", "")
                except:
                    markdown = str(response)
            
            if not markdown:
                logger.error(f"No markdown content extracted from {url}")
                return {"markdown": ""}
            
            # Save to cache
            await db.crawl_cache.update_one(
                {"url": url},
                {"$set": {
                    "markdown": markdown,
                    "crawled_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(hours=24),
                }},
                upsert=True
            )
            return {"markdown": markdown, "provider": "Firecrawl", "cached": False}
        except Exception as e:
            logger.error(f"Crawler failed for {url}: {e}. Using degraded fallback.")
            return {
                "markdown": f"Unable to crawl {url}. Degraded fallback content was generated after provider failure: {e}",
                "provider": "crawler-fallback",
                "cached": False,
                "degraded": True,
            }

    def health(self) -> dict:
        return {
            "configured": self.app is not None,
            "available": not self.breaker.is_open,
        }
