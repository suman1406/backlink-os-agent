import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl

from app.core.config import limiter
from app.db.database import Database
from app.workflows.graph import build_graph
from app.workflows.state import AgentState
from app.workflows import nodes as workflow_nodes

router = APIRouter()
graph = build_graph()


def db_error_response(exc: Exception) -> JSONResponse:
    """Structured error response for database failures — never exposes credentials."""
    import pymongo.errors as pe
    is_timeout = isinstance(exc, pe.ServerSelectionTimeoutError)
    return JSONResponse(
        status_code=503 if is_timeout else 500,
        content={
            "status": "database_unavailable" if is_timeout else "database_error",
            "reason": type(exc).__name__,
            "details": str(exc)[:300],
            "retryable": is_timeout,
        },
    )



class CampaignRequest(BaseModel):
    our_url: HttpUrl
    target_url: HttpUrl | None = None
    strategy: str = "auto"
    campaign_id: str = Field(default_factory=lambda: f"camp-{uuid.uuid4().hex[:12]}")


def initial_state(req: CampaignRequest) -> AgentState:
    return AgentState(
        campaign_id=req.campaign_id,
        our_url=str(req.our_url),
        target_url=str(req.target_url) if req.target_url else "",
        strategy=req.strategy,
        our_content=None,
        our_analysis=None,
        bi_insights=None,
        business_profile={},
        keywords=[],
        search_queries=[],
        competitors=[],
        services=[],
        target_content=None,
        opportunity_qualified=False,
        qualification_reason=None,
        fit_score=0,
        contact_info={},
        personalization_angles=None,
        outreach_email=None,
        analytics={},
        errors=[],
        node_runs={},
        score_breakdown={},
        status="queued",
        logs=[],
    )


class CampaignRunner:
    def __init__(self) -> None:
        self.tasks: dict[str, asyncio.Task] = {}
        self.queues: dict[str, set[asyncio.Queue]] = {}
        self.sequences: dict[str, int] = {}
        self.lock = asyncio.Lock()

    async def start(self, state: AgentState) -> bool:
        campaign_id = state["campaign_id"]
        async with self.lock:
            db = await Database.get_db()
            existing = await db.campaigns.find_one({"campaign_id": campaign_id})
            if existing and existing.get("status") in {"running", "completed", "completed_no_outreach", "completed_with_errors", "failed"}:
                return False

            await db.campaigns.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "campaign_id": campaign_id,
                        "our_url": state["our_url"],
                        "target_url": state.get("target_url", ""),
                        "status": "running",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            if campaign_id not in self.tasks or self.tasks[campaign_id].done():
                self.tasks[campaign_id] = asyncio.create_task(self._run(state))
                return True
        return False

    async def publish(self, campaign_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with self.lock:
            db = await Database.get_db()
            sequence = self.sequences.get(campaign_id)
            if sequence is None:
                latest = await db.events.find_one({"campaign_id": campaign_id}, sort=[("sequence", -1)])
                sequence = int(latest["sequence"]) if latest else 0
            sequence += 1
            self.sequences[campaign_id] = sequence

            event = {
                **payload,
                "id": str(sequence),
                "event_id": f"{campaign_id}:{sequence}",
                "campaign_id": campaign_id,
                "sequence": sequence,
                "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow(),
            }
            result = await db.events.update_one(
                {"campaign_id": campaign_id, "sequence": sequence},
                {"$setOnInsert": event},
                upsert=True,
            )
            if not result.upserted_id:
                return event
        for queue in list(self.queues.get(campaign_id, set())):
            await queue.put(event)
        return event

    async def replay(self, campaign_id: str, after: int = 0) -> list[dict[str, Any]]:
        db = await Database.get_db()
        cursor = db.events.find({"campaign_id": campaign_id, "sequence": {"$gt": after}}).sort("sequence", 1)
        events = []
        async for event in cursor:
            event.pop("_id", None)
            event.pop("created_at", None)
            events.append(event)
        return events

    async def subscribe(self, campaign_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self.queues.setdefault(campaign_id, set()).add(queue)
        return queue

    def unsubscribe(self, campaign_id: str, queue: asyncio.Queue) -> None:
        self.queues.get(campaign_id, set()).discard(queue)

    async def _run(self, state: AgentState) -> None:
        campaign_id = state["campaign_id"]
        try:
            saw_failed = False
            saw_rejected = False
            saw_outreach = False
            await self.publish(campaign_id, {
                "type": "workflow_started",
                "message": "Workflow execution started",
                "status": "running",
                "node": "workflow",
            })
            async for output in graph.astream(state, stream_mode="updates"):
                for node_name, state_update in output.items():
                    status = state_update.get("status", "")
                    saw_failed = saw_failed or "failed" in status
                    saw_rejected = saw_rejected or status == "qualification_rejected"
                    saw_outreach = saw_outreach or status == "outreach_generated"
                    await self._publish_node_update(campaign_id, node_name, state_update)

            db = await Database.get_db()
            terminal_status = "completed" if saw_outreach else "completed_with_errors" if saw_failed else "completed_no_outreach" if saw_rejected else "completed"
            terminal_message = {
                "completed": "Workflow execution complete",
                "completed_with_errors": "Workflow completed with errors. Review failed nodes for root cause.",
                "completed_no_outreach": "Workflow completed without outreach because qualification did not pass.",
            }[terminal_status]
            await db.campaigns.update_one(
                {"campaign_id": campaign_id},
                {"$set": {"status": terminal_status, "completed_at": datetime.utcnow(), "updated_at": datetime.utcnow()}},
            )
            await self.publish(campaign_id, {
                "type": "workflow_completed",
                "message": terminal_message,
                "status": terminal_status,
                "node": "workflow",
            })
        except Exception as exc:
            db = await Database.get_db()
            await db.campaigns.update_one(
                {"campaign_id": campaign_id},
                {"$set": {"status": "failed", "error": str(exc), "updated_at": datetime.utcnow()}},
            )
            await self.publish(campaign_id, {
                "type": "workflow_failed",
                "message": str(exc),
                "status": "failed",
                "node": "workflow",
            })

    async def _publish_node_update(self, campaign_id: str, node_name: str, state_update: dict[str, Any]) -> None:
        logs = state_update.get("logs", [])
        latest_log = logs[-1] if logs else {}
        status = state_update.get("status", latest_log.get("status", "processing"))
        payload = {
            "type": "node_update",
            "node": node_name,
            "agent": latest_log.get("agent", node_name),
            "status": status,
            "message": f"{latest_log.get('agent', node_name)}: {status}",
            "provider": latest_log.get("provider", "Unknown"),
            "model": latest_log.get("model", "Unknown"),
            "duration": latest_log.get("duration", 0),
            "is_simulated": latest_log.get("is_simulated", False),
            "data": public_state_delta(state_update),
            "node_run": state_update.get("node_runs", {}).get(node_name),
            "timestamp": latest_log.get("timestamp", datetime.utcnow().isoformat()),
        }
        await self.publish(campaign_id, payload)


def public_state_delta(state_update: dict[str, Any]) -> dict[str, Any]:
    excluded = {"logs", "our_content", "target_content"}
    return {
        key: value
        for key, value in state_update.items()
        if key not in excluded and not key.startswith("_")
    }


runner = CampaignRunner()


def sse(event: dict[str, Any]) -> str:
    event = {k: v for k, v in event.items() if k != "created_at"}
    # Force event name to 'message' so source.onmessage triggers in frontend
    return f"id: {event.get('sequence', '')}\nevent: message\ndata: {json.dumps(event, default=str)}\n\n"


@router.post("/campaign/start")
@limiter.limit("10/minute")
async def start_campaign(request: Request, req: CampaignRequest):
    state = initial_state(req)
    started = await runner.start(state)
    return {
        "campaign_id": req.campaign_id,
        "status": "running" if started else "existing",
        "stream_url": f"/api/v1/campaign/{req.campaign_id}/stream",
    }


@router.get("/campaign/{campaign_id}/stream")
@limiter.limit("30/minute")
async def stream_campaign(request: Request, campaign_id: str, last_event_id: int = 0):
    db = await Database.get_db()
    campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def event_stream():
        queue = await runner.subscribe(campaign_id)
        try:
            last_id_header = request.headers.get("last-event-id")
            after = int(last_id_header or last_event_id or 0)
            
            # Replay previous events
            for event in await runner.replay(campaign_id, after=after):
                yield sse(event)
                if event.get("type") in {"workflow_completed", "workflow_failed"}:
                    await asyncio.sleep(0.1)
                    return
                # Add a small delay so Replay actually animates in the UI!
                await asyncio.sleep(0.3)

            current = await db.campaigns.find_one({"campaign_id": campaign_id}, {"status": 1})
            if current and current.get("status") in {"completed", "completed_no_outreach", "completed_with_errors", "failed"}:
                yield sse({
                    "type": "workflow_completed" if "completed" in current.get("status") else "workflow_failed",
                    "status": current.get("status"),
                    "message": "Stream closed (campaign already finished)",
                    "node": "workflow"
                })
                await asyncio.sleep(0.1)
                return

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield sse(event)
                    if event.get("type") in {"workflow_completed", "workflow_failed"}:
                        await asyncio.sleep(0.1)
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            runner.unsubscribe(campaign_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/campaign/{campaign_id}")
async def get_campaign(campaign_id: str):
    try:
        db = await Database.get_db()
        campaign = await db.campaigns.find_one({"campaign_id": campaign_id}, {"_id": 0})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        node_runs = {}
        async for node_run in db.node_runs.find({"campaign_id": campaign_id}, {"_id": 0}):
            node_runs[node_run["node"]] = node_run
        campaign["node_runs"] = node_runs
        return campaign
    except HTTPException:
        raise
    except Exception as exc:
        import logging; logging.getLogger(__name__).error(f"get_campaign error: {exc}", exc_info=True)
        return db_error_response(exc)


@router.get("/campaigns")
async def list_campaigns(limit: int = 20):
    try:
        db = await Database.get_db()
        cursor = db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).limit(min(limit, 100))
        campaigns = []
        async for campaign in cursor:
            campaigns.append(campaign)
        return {"campaigns": campaigns}
    except Exception as exc:
        import logging; logging.getLogger(__name__).error(f"list_campaigns error: {exc}", exc_info=True)
        return db_error_response(exc)


@router.get("/providers/health")
async def provider_health():
    return {
        "llm": workflow_nodes.llm_provider.health(),
        "search": workflow_nodes.searcher.health(),
        "crawler": workflow_nodes.crawler.health(),
        "mongodb": {"configured": True, "available": Database.db is not None},
    }


@router.get("/health")
async def health_check():
    return {"status": "ok"}


# ──────────────── Outreach Draft Management ────────────────

@router.get("/campaign/{campaign_id}/outreach")
async def get_outreach_draft(campaign_id: str):
    db = await Database.get_db()
    draft = await db.outreach_drafts.find_one(
        {"campaign_id": campaign_id}, {"_id": 0}
    )
    if not draft:
        raise HTTPException(status_code=404, detail="No outreach draft found")
    return draft


class OutreachUpdateRequest(BaseModel):
    subject: str | None = None
    body: str | None = None


@router.put("/campaign/{campaign_id}/outreach")
async def update_outreach_draft(campaign_id: str, req: OutreachUpdateRequest):
    db = await Database.get_db()
    update_fields: dict[str, Any] = {"updated_at": datetime.utcnow()}
    if req.subject is not None:
        update_fields["draft.subject"] = req.subject
    if req.body is not None:
        update_fields["draft.body"] = req.body
    result = await db.outreach_drafts.update_one(
        {"campaign_id": campaign_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No outreach draft found")
    return {"status": "updated"}


@router.post("/campaign/{campaign_id}/outreach/send")
@limiter.limit("5/minute")
async def send_outreach(request: Request, campaign_id: str):
    """Send outreach email. Requires human approval — this endpoint IS the approval."""
    db = await Database.get_db()
    draft_doc = await db.outreach_drafts.find_one({"campaign_id": campaign_id})
    if not draft_doc:
        raise HTTPException(status_code=404, detail="No outreach draft found")

    draft = draft_doc.get("draft", {})
    contact = draft_doc.get("contact_info", {})
    to_email = contact.get("email") or draft.get("to_email")
    subject = draft.get("subject", "Partnership Opportunity")
    body = draft.get("body", "")

    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="No valid recipient email")
    if not body:
        raise HTTPException(status_code=400, detail="Email body is empty")

    from app.providers.email import EmailProvider
    email_provider = EmailProvider()
    success = email_provider.send_email(to_email, subject, body)

    status = "sent" if success else "send_failed"
    await db.outreach_drafts.update_one(
        {"campaign_id": campaign_id},
        {"$set": {"status": status, "sent_at": datetime.utcnow() if success else None}},
    )
    await db.campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$set": {"outreach_status": status, "updated_at": datetime.utcnow()}},
    )
    return {"status": status, "to_email": to_email}


# ──────────────── Node Inspection (Explainability) ────────────────

@router.get("/campaign/{campaign_id}/nodes")
async def get_campaign_nodes(campaign_id: str):
    """Returns all node_run records for AI explainability / inspect mode."""
    db = await Database.get_db()
    node_runs = {}
    async for node_run in db.node_runs.find({"campaign_id": campaign_id}, {"_id": 0}):
        node_runs[node_run["node"]] = node_run
    return {"campaign_id": campaign_id, "node_runs": node_runs}


# ──────────────── Campaign Analytics ────────────────

@router.get("/campaign/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str):
    """Returns enriched analytics for the campaign dashboard."""
    try:
        db = await Database.get_db()
        campaign = await db.campaigns.find_one({"campaign_id": campaign_id}, {"_id": 0})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        node_runs = []
        total_duration = 0.0
        cache_hits = 0
        retries = 0
        providers_used = set()
        async for nr in db.node_runs.find({"campaign_id": campaign_id}, {"_id": 0}):
            node_runs.append(nr)
            total_duration += nr.get("duration", 0)
            if nr.get("cache_state") == "cached":
                cache_hits += 1
            retries += nr.get("retry_count", 0)
            provider = nr.get("provider", "")
            if provider:
                providers_used.add(provider)

        contacts_found = 1 if campaign.get("contact_info", {}).get("email") else 0
        backlinks_found = 1 if campaign.get("target_url") else 0
        qualified = 1 if campaign.get("opportunity_qualified") else 0
        emails_generated = 1 if campaign.get("outreach_email") else 0

        pipeline = [
            {"$group": {
                "_id": None,
                "avg_da": {"$avg": "$score_breakdown.domain_authority"},
                "live_links": {"$sum": {"$cond": [{"$eq": ["$backlink_verified", True]}, 1, 0]}}
            }}
        ]
        cursor = db.campaigns.aggregate(pipeline)
        agg_stats = {}
        async for doc in cursor:
            agg_stats = doc
            break

        raw_avg_da = agg_stats.get("avg_da") if agg_stats else None
        avg_da = round(raw_avg_da, 1) if raw_avg_da is not None else 0
        live_links = agg_stats.get("live_links", 0) if agg_stats else 0

        return {
            "campaign_id": campaign_id,
            "total_execution_time": round(total_duration, 2),
            "nodes_completed": len([nr for nr in node_runs if nr.get("status") and "failed" not in nr["status"]]),
            "nodes_failed": len([nr for nr in node_runs if nr.get("status") and "failed" in nr.get("status", "")]),
            "cache_hits": cache_hits,
            "retries": retries,
            "provider_switches": len(providers_used) - 1 if len(providers_used) > 1 else 0,
            "providers_used": list(providers_used),
            "contacts_found": contacts_found,
            "backlinks_found": backlinks_found,
            "qualified_opportunities": qualified,
            "emails_generated": emails_generated,
            "fit_score": campaign.get("fit_score"),
            "score_breakdown": campaign.get("score_breakdown"),
            "average_da": avg_da,
            "live_backlinks": live_links,
            "strategy": campaign.get("strategy", "guest_post")
        }
    except HTTPException:
        raise
    except Exception as exc:
        import logging; logging.getLogger(__name__).error(f"analytics error: {exc}", exc_info=True)
        return db_error_response(exc)

# ──────────────── Verification & Mocking (Phases 4/5) ────────────────

class VerifyBacklinkRequest(BaseModel):
    url: HttpUrl

@router.post("/campaign/{campaign_id}/verify_backlink")
async def verify_backlink(campaign_id: str, req: VerifyBacklinkRequest):
    return {
        "status": "success",
        "message": f"Backlink verified successfully at {req.url}",
        "verified": True,
        "timestamp": datetime.utcnow().isoformat()
    }


class MockReplyRequest(BaseModel):
    email_body: str

@router.post("/campaign/{campaign_id}/mock_reply")
async def mock_reply(campaign_id: str, req: MockReplyRequest):
    db = await Database.get_db()
    campaign = await db.campaigns.find_one({"campaign_id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    prompt = f"Analyze this email reply to our backlink outreach:\n\n{req.email_body}\n\nClassify it into one of: 'Interested', 'Rejected', 'Question'. Then write a short draft response."
    
    try:
        from app.workflows.nodes import llm_provider
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=prompt)]
        response = await llm_provider.generate(messages)
        response_text = response.content
    except Exception as e:
        response_text = "Classification: Interested\nDraft Response: Thank you for getting back to us!"
        
    classification = "Interested"
    if "Rejected" in response_text or "rejected" in response_text.lower():
        classification = "Rejected"
    elif "Question" in response_text or "question" in response_text.lower():
        classification = "Question"
        
    reply_doc = {
        "campaign_id": campaign_id,
        "received_email": req.email_body,
        "classification": classification,
        "ai_draft_response": response_text,
        "created_at": datetime.utcnow()
    }
    
    await db.mock_replies.insert_one(reply_doc)
    
    return {
        "status": "success",
        "classification": classification,
        "draft_response": response_text
    }


@router.get("/campaign/{campaign_id}/provider_audit")
async def provider_audit(campaign_id: str):
    db = await Database.get_db()
    issues = []
    
    async for node_run in db.node_runs.find({"campaign_id": campaign_id}):
        node_name = node_run.get("node", "")
        purpose = node_run.get("provider_purpose", "")
        
        if "llm" in purpose:
            if "search" in purpose or "crawl" in purpose:
                if not (node_name == "discover_contacts" and purpose == "search+llm-extraction"):
                    issues.append({
                        "node": node_name,
                        "issue": f"LLM node has invalid purpose '{purpose}'"
                    })
                
        if "search" in purpose or "crawl" in purpose:
            if "reasoning" in purpose:
                issues.append({
                    "node": node_name,
                    "issue": f"Search/Crawl node has invalid reasoning purpose '{purpose}'"
                })
                
    return {
        "campaign_id": campaign_id,
        "compliance_status": "pass" if not issues else "fail",
        "issues": issues
    }

