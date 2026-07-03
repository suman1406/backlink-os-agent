from typing import TypedDict, List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
import operator

class LogEntry(TypedDict):
    agent: str
    task: str
    status: str
    duration: float
    provider: str
    model: str
    confidence: float
    is_simulated: bool
    timestamp: str

class AgentState(TypedDict):
    campaign_id: str
    target_url: str
    our_url: str
    
    # Context
    our_content: Optional[str]
    our_analysis: Optional[str]
    bi_insights: Optional[str]
    business_profile: Annotated[Dict[str, Any], lambda a, b: {**(a or {}), **(b or {})}]
    strategy: Optional[str]
    keywords: Annotated[List[str], operator.add]
    search_queries: Annotated[List[str], operator.add]
    competitors: Annotated[List[str], operator.add]
    services: Annotated[List[str], operator.add]
    
    # Target (use reducer to preserve first non-empty value)
    target_content: Annotated[Optional[str], lambda a, b: b if b else a]
    opportunity_qualified: Annotated[bool, lambda a, b: a or b]  # True if either is True
    qualification_reason: Annotated[Optional[str], lambda a, b: b if b else a]  # Preserve latest
    fit_score: Annotated[int, lambda a, b: max(a or 0, b or 0)]  # Use highest score
    
    contact_info: Annotated[Dict[str, Any], lambda a, b: {**a, **b} if a and b else (b or a or {})]  # Merge dicts
    personalization_angles: Optional[str]
    outreach_email: Annotated[Optional[Dict[str, Any]], lambda a, b: b if b else a]
    generated_article: Annotated[Optional[Dict[str, Any]], lambda a, b: b if b else a]
    analytics: Annotated[Dict[str, Any], lambda a, b: {**(a or {}), **(b or {})}]
    errors: Annotated[List[Dict[str, Any]], operator.add]
    node_runs: Annotated[Dict[str, Any], lambda a, b: {**(a or {}), **(b or {})}]
    score_breakdown: Annotated[Dict[str, Any], lambda a, b: {**(a or {}), **(b or {})}]
    
    # Tracking
    status: Annotated[str, lambda a, b: b]
    logs: Annotated[List[LogEntry], operator.add]
    
class AgentResponseSchema(BaseModel):
    content: str = Field(description="The response content")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
