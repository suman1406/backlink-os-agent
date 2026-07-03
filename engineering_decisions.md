# Engineering Decisions

This document outlines the architectural and engineering decisions made during the 24-hour development of **AI Backlink OS**.

---

## 1. Multi-Agent Orchestration (LangGraph)
- **Decision:** Use **LangGraph** instead of a linear LangChain or standard sequential script.
- **Rationale:** Backlink outreach is inherently non-linear. An opportunity might fail qualification (requiring the graph to stop or pivot), or a search query might return no results (requiring queries to be regenerated). LangGraph enables stateful, cyclic graphs with native support for:
  - Conditional routing (e.g., generating articles only for qualified `guest_post` opportunities).
  - Storing complete, step-by-step state logs in MongoDB for real-time explainability.
  - Granular node tracking for retry and fallback logic.

---

## 2. API Resilience & Fallback Chain
- **Decision:** Built a multi-LLM fallback chain (Gemini 2.5 Flash ➡️ Cerebras 120B ➡️ Groq Llama 3.1) guarded by circuit breakers and rate limiters.
- **Rationale:** Free-tier API keys have extremely low Rate Limits (TPM/RPM). To prevent campaign execution from crashing mid-way, the system dynamically switches providers:
  - **Gemini 2.5 Flash** acts as the primary reasoning engine.
  - **Cerebras** (extremely fast inference) handles extraction and parsing tasks.
  - **Groq** serves as the final robust fallback for text generation.

---

## 3. Database Layer: Switch to MongoDB Atlas
- **Decision:** Switched from a local Dockerized MongoDB database to **MongoDB Atlas**.
- **Rationale:** The AWS EC2 micro instance allocated for this task has an 8GB storage limit, which was completely exhausted by build caches and Docker volumes. Offloading the database to Atlas freed up **1.6 GB** of disk space on the EC2 host.
- **Driver Decision:** Used `motor` (AsyncIOMotorClient) instead of `pymongo` (synchronous) for all database operations inside FastAPI routes. This prevents thread blocking and resolves event loop deadlock regressions under heavy parallel usage.

---

## 4. Next.js Rewrite Proxy for Vercel
- **Decision:** Configured a native rewrite proxy in `next.config.ts` mapping `/api_backend` to the EC2 host.
- **Rationale:** Modern browsers enforce strict **Mixed Content Policies**, blocking HTTPS sites (like Vercel) from fetching from insecure HTTP backends (like raw EC2 IPs). Using Vercel's edge network to rewrite and proxy requests internally solves the mixed-content block without requiring domain purchases or complex Let's Encrypt configurations on the EC2 instance.

---

## 5. Prospect Memory (ChromaDB)
- **Decision:** Initialized a local **ChromaDB** instance to persist crawled content embeddings.
- **Rationale:** To avoid spamming the same target domain across multiple runs or different campaigns, ChromaDB acts as a vector-based prospect deduplicator. Before qualification, target URLs are verified against vector memories.

---

## 6. Real-Time Streaming (Server-Sent Events)
- **Decision:** Used Server-Sent Events (SSE) instead of WebSockets or polling.
- **Rationale:** SSE is lightweight, unidirectional, and runs natively over standard HTTP. It allows the LangGraph execution flow to stream log nodes directly to the dashboard, providing the user with immediate visibility of the agent's "thinking process" and visual proof of execution.
