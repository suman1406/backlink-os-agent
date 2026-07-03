import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_start_campaign_sse():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/campaign/start",
            json={
                "our_url": "https://example.com/our-post",
                "target_url": "https://example.com/target-post",
                "campaign_id": "test-123"
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_id"] == "test-123"
    assert data["stream_url"] == "/api/v1/campaign/test-123/stream"

@pytest.mark.asyncio
async def test_rate_limiting():
    # Make multiple requests to trigger rate limit
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for _ in range(10):
            await ac.post(
                "/api/v1/campaign/start",
                json={
                    "our_url": "https://example.com/our-post",
                    "target_url": "https://example.com/target-post",
                    "campaign_id": "test-123"
                }
            )
        
        # 11th request should be rate limited
        response = await ac.post(
            "/api/v1/campaign/start",
            json={
                "our_url": "https://example.com/our-post",
                "target_url": "https://example.com/target-post",
                "campaign_id": "test-123"
            }
        )
        assert response.status_code == 429
