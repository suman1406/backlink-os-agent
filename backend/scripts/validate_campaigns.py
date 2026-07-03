import asyncio
import json
import time

import httpx


TARGETS = [
    "https://www.boat-lifestyle.com/",
    "https://secondorigin.vercel.app/",
    "https://www.notion.so/",
]

REQUIRED_NODES = {
    "crawl_website",
    "analyze_business",
    "extract_keywords",
    "discover_competitors",
    "discover_backlinks",
    "discover_contacts",
    "extract_services",
    "qualify_opportunity",
}


async def validate_target(client: httpx.AsyncClient, target: str) -> dict:
    campaign_id = f"e2e-{int(time.time() * 1000)}"
    start = await client.post(
        "http://localhost:8000/api/v1/campaign/start",
        json={"campaign_id": campaign_id, "our_url": target},
        timeout=20,
    )
    start.raise_for_status()

    events = []
    nodes = set()
    statuses = {}
    terminal = None
    async with client.stream(
        "GET",
        f"http://localhost:8000/api/v1/campaign/{campaign_id}/stream",
        timeout=180,
    ) as stream:
        async for line in stream.aiter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line.removeprefix("data: "))
            events.append(event)
            if event.get("type") == "node_update":
                nodes.add(event.get("node"))
                statuses[event.get("node")] = event.get("status")
            if event.get("type") in {"workflow_completed", "workflow_failed"}:
                terminal = event
                break

    snapshot = (await client.get(f"http://localhost:8000/api/v1/campaign/{campaign_id}", timeout=20)).json()
    missing = sorted(REQUIRED_NODES - nodes)
    return {
        "target": target,
        "campaign_id": campaign_id,
        "terminal_status": terminal.get("status") if terminal else "missing_terminal",
        "events": len(events),
        "nodes": sorted(nodes),
        "missing_required_nodes": missing,
        "outreach": statuses.get("generate_outreach", "not_emitted"),
        "fit_score": snapshot.get("fit_score"),
        "persisted_node_runs": len(snapshot.get("node_runs", {})),
        "persisted_status": snapshot.get("status"),
    }


async def main():
    async with httpx.AsyncClient() as client:
        health = await client.get("http://localhost:8000/health", timeout=10)
        health.raise_for_status()
        results = []
        for target in TARGETS:
            results.append(await validate_target(client, target))
        print(json.dumps(results, indent=2))

        critical_failures = [
            result for result in results
            if result["missing_required_nodes"] or result["terminal_status"] in {"missing_terminal", "failed"}
        ]
        if critical_failures:
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
