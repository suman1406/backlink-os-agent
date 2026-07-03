import logging
from typing import List, Dict, Any
from app.core.config import settings
from app.core.resilience import CircuitBreaker, AsyncRateLimiter, retry_async
from langchain_community.tools.tavily_search import TavilySearchResults

logger = logging.getLogger(__name__)

class SearchProvider:
    def __init__(self):
        self.use_mock = settings.USE_MOCK_SEARCH
        self.breaker = CircuitBreaker()
        self.rate_limiter = AsyncRateLimiter(max_calls=30, window_seconds=60)
        if not self.use_mock and settings.TAVILY_API_KEY:
            self.tool = TavilySearchResults(
                tavily_api_key=settings.TAVILY_API_KEY,
                max_results=3
            )
        else:
            self.tool = None
            if not self.use_mock:
                logger.warning("No TAVILY_API_KEY provided, falling back to mock search.")
                self.use_mock = True

    async def search(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Executing search for query: {query}")
        if self.use_mock:
            return [{"url": "https://example.com/mock-result", "content": f"Mock result for {query}", "provider": "search-mock", "degraded": True, "cached": False}]
        
        try:
            await self.rate_limiter.acquire()
            results = await retry_async(
                lambda: self.tool.ainvoke({"query": query}),
                attempts=2,
                timeout=15.0,
                breaker=self.breaker,
            )
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}. Falling back to mock.")
            self.use_mock = True
            return [{"url": "https://example.com/mock-result", "content": f"Mock result for {query} (Simulated Fallback)", "provider": "search-fallback", "degraded": True, "cached": False}]

    def health(self) -> dict:
        return {
            "configured": self.tool is not None,
            "available": not self.breaker.is_open,
            "mock": self.use_mock,
        }
