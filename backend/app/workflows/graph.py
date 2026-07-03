from langgraph.graph import StateGraph, END
from app.workflows.state import AgentState
from app.workflows.nodes import (
    crawl_website,
    analyze_business,
    strategy_planner,
    extract_keywords,
    discover_competitors,
    extract_services,
    discover_backlinks,
    discover_contacts,
    qualify_opportunity,
    generate_outreach,
    generate_article,
    mock_publish_article,
    verify_backlink
)

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("crawl_website", crawl_website)
    workflow.add_node("analyze_business", analyze_business)
    workflow.add_node("strategy_planner", strategy_planner)
    workflow.add_node("extract_keywords", extract_keywords)
    workflow.add_node("discover_competitors", discover_competitors)
    workflow.add_node("extract_services", extract_services)
    workflow.add_node("discover_backlinks", discover_backlinks)
    workflow.add_node("discover_contacts", discover_contacts)
    workflow.add_node("qualify_opportunity", qualify_opportunity)
    workflow.add_node("generate_outreach", generate_outreach)
    workflow.add_node("generate_article", generate_article)
    workflow.add_node("mock_publish_article", mock_publish_article)
    workflow.add_node("verify_backlink", verify_backlink)
    
    # 1. Crawl website (2-5s) -> Yields instantly
    workflow.set_entry_point("crawl_website")
    
    # 2. Sequential BI extraction
    workflow.add_edge("crawl_website", "analyze_business")
    
    # 3. Strategy Planning and Extract keywords (required for search)
    workflow.add_edge("analyze_business", "strategy_planner")
    workflow.add_edge("strategy_planner", "extract_keywords")
    
    # 4. Enrich business context before discovery
    workflow.add_edge("extract_keywords", "discover_competitors")

    # 5. Backlinks discovery sets target_content and target_url.
    workflow.add_edge("discover_competitors", "discover_backlinks")

    # 6. Run enrichment deterministically. This avoids duplicate fan-in execution
    # of qualification and keeps SSE ordering exact for the UI.
    workflow.add_edge("discover_backlinks", "discover_contacts")
    workflow.add_edge("discover_contacts", "extract_services")
    
    # 7. Qualification requires all discoveries to complete
    workflow.add_edge("extract_services", "qualify_opportunity")
    
    # 8. Generate outreach based on qualification
    def qualification_router(state: AgentState) -> str:
        # Both qualified and borderline cases should generate outreach drafts
        # (borderline drafts require human review before sending)
        if state.get("opportunity_qualified", False):
            return "generate_outreach"
        return END

    workflow.add_conditional_edges(
        "qualify_opportunity",
        qualification_router,
        {
            "generate_outreach": "generate_outreach",
            END: END
        }
    )
    
    # 9. Generate article conditionally if guest post
    def article_router(state: AgentState) -> str:
        if state.get("opportunity_qualified", False) and state.get("strategy") == "guest_post":
            return "generate_article"
        return END
        
    workflow.add_conditional_edges(
        "generate_outreach",
        article_router,
        {
            "generate_article": "generate_article",
            END: END
        }
    )
    
    workflow.add_edge("generate_article", "mock_publish_article")
    workflow.add_edge("mock_publish_article", "verify_backlink")
    workflow.add_edge("verify_backlink", END)
    
    return workflow.compile()
