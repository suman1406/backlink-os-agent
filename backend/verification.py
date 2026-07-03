import asyncio
import httpx
import json
import time
from datetime import datetime

async def verify_infrastructure():
    results = []
    print("\n--- Starting Autonomous Verification Dashboard ---\n")
    
    # 1. Backend Health
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/health")
            if resp.status_code == 200:
                results.append(("Backend", "PASS ✅", f"{time.time()-start:.3f}s", "Health endpoint 200 OK"))
            else:
                results.append(("Backend", "FAIL ❌", f"{time.time()-start:.3f}s", f"Status {resp.status_code}"))
    except Exception as e:
        results.append(("Backend", "FAIL ❌", f"{time.time()-start:.3f}s", str(e)))

    # 2. End-to-End Campaign stream
    start_time = time.time()
    first_event_time = None
    first_crawl_time = None
    first_bi_time = None
    nodes_executed = set()
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {
                "our_url": "https://www.zomato.com/",
                "campaign_id": f"verify-{int(time.time())}"
            }
            print(f"Triggering Campaign: {payload['campaign_id']}")
            
            async with client.stream("POST", "http://localhost:8000/api/v1/campaign/start", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        
                        if first_event_time is None:
                            first_event_time = time.time() - start_time
                            results.append(("SSE Stream", "PASS ✅", f"{first_event_time:.3f}s", "Time to First SSE Event"))
                        
                        agent = data.get("Agent")
                        status = data.get("Status")
                        
                        if agent:
                            nodes_executed.add(agent)
                            print(f"[{time.time()-start_time:.2f}s] Streamed Event: {agent} -> {status} (Provider: {data.get('Provider')})")
                        
                        if status == "website_crawled" and first_crawl_time is None:
                            first_crawl_time = time.time() - start_time
                            results.append(("Firecrawl", "PASS ✅", f"{first_crawl_time:.3f}s", "Initial crawl yielded"))
                            
                        if status == "bi_generated" and first_bi_time is None:
                            first_bi_time = time.time() - start_time
                            results.append(("Primary LLM", "PASS ✅", f"{first_bi_time:.3f}s", f"BI insights yielded via {data.get('Provider')}"))
                            
                        if status == "completed":
                            total_time = time.time() - start_time
                            results.append(("LangGraph", "PASS ✅", f"{total_time:.3f}s", f"Parallel Graph Completed ({len(nodes_executed)} nodes)"))
                            break

    except Exception as e:
         results.append(("Campaign", "FAIL ❌", f"{time.time()-start_time:.3f}s", str(e)))

    print("\n| Component | Status | Time | Evidence |")
    print("|---|---|---|---|")
    for r in results:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")

if __name__ == "__main__":
    asyncio.run(verify_infrastructure())
