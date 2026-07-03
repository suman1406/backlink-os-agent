# AI Backlink OS

An AI-powered, autonomous backlink outreach platform built to demonstrate the ability to orchestrate complex AI workflows, design scalable architectures, and deliver an end-to-end MVP. 

This platform acts as an autonomous SEO outreach specialist: it understands a target website, dynamically discovers backlink opportunities, qualifies prospects, extracts contact info using SerpAPI, and generates highly personalized outreach emails and SEO-optimized guest articles.

---

## 🏗️ Architecture & Technologies Used

The system is split into a Next.js frontend and a FastAPI backend, orchestrated by a robust LangGraph multi-agent state machine.

### Core Stack
- **Frontend:** Next.js 15 (App Router), React, Tailwind CSS, shadcn/ui, Framer Motion
- **Backend:** FastAPI, Python 3.12+, LangGraph
- **Database:** MongoDB (Stores unstructured LangGraph state and execution histories)
- **Vector DB:** ChromaDB (Prospect memory and deduplication)
- **AI & Data Providers:** 
  - LiteLLM (OpenAI-compatible abstraction for Gemini, Groq, Cerebras)
  - Firecrawl (Deep website scraping and intelligence)
  - Tavily Search (Targeted opportunity discovery)
  - SerpAPI (Google Search for exact Contact & LinkedIn extraction)
- **Deployment:** Docker & Docker Compose

---

## 🚀 Vercel Deployment Capabilities

When considering a production deployment, it's crucial to understand what can and cannot be hosted on Vercel:

| Component | Can it be hosted on Vercel? | Explanation |
| :--- | :--- | :--- |
| **Frontend (Next.js)** | ✅ **YES** | Vercel is the native platform for Next.js. It will host the frontend UI, handle Server-Sent Events (SSE) subscriptions seamlessly, and serve static assets globally. |
| **Backend (FastAPI)** | ❌ **NO** | While Vercel supports Python serverless functions, they have strict execution timeouts (10s on Hobby, 60s on Pro). Our LangGraph workflow (scraping, LLM generation, SerpAPI calls) takes minutes to complete. The backend **must** be deployed to a long-running container service (e.g., Render, Railway, AWS ECS, or a VPS). |
| **Database (MongoDB)** | ❌ **NO** | Vercel does not host databases directly. Use MongoDB Atlas (a managed cloud database). |
| **Vector DB (Chroma)** | ❌ **NO** | ChromaDB relies on persistent disk storage (SQLite). Vercel's file system is ephemeral and read-only. You must use a cloud vector database (like Pinecone) or host Chroma on a persistent VPS. |

### 🚢 Deploying the Backend to Render or Railway

Because Vercel cannot host the FastAPI backend, we highly recommend deploying it to **Render** or **Railway**. Both platforms support long-running Docker containers and Web Services without strict timeout limits, which is essential for our LangGraph agents.

**Option A: Railway (Recommended for Docker)**
1. Connect your GitHub repository to Railway.
2. Select the `backend/` directory as the root. Railway will automatically detect the Dockerfile (if present) or the Python environment.
3. If not using Docker, set the Start Command to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add a **Persistent Volume** in Railway and mount it to `/app/chroma_db` to ensure ChromaDB vector storage persists across deployments.
5. Provide the necessary Environment Variables (LLM, Tavily, Firecrawl, SerpAPI).

**Option B: Render (Web Service)**
1. Create a new "Web Service" in Render and connect your repository.
2. Set the Root Directory to `backend/`.
3. Select "Python 3" environment. Set Build Command to `pip install -r requirements.txt` and Start Command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. To persist ChromaDB on Render, you must upgrade to a paid tier to attach a "Disk" to your Web Service, mounted at `/app/chroma_db`. Otherwise, the vector memory will reset on every deploy.

---

## 📊 Full Compliance & "Why Mock?" Justification

To deliver this MVP rapidly while demonstrating full system capabilities, certain features were fully implemented while others were intentionally mocked due to external constraints.

### ✅ Fully Implemented Features
| Feature | Implementation Detail |
| :--- | :--- |
| **1. Website Intelligence** | LangGraph `analyze_business` & `extract_keywords` nodes use Firecrawl & LLMs to extract core business logic. |
| **2. Dynamic Opportunity Discovery** | Fully implemented! The user selects a strategy (or AI Auto-Selects). The AI Planner generates a highly optimized search query (e.g., `site:target.com intitle:"submit podcast"`), overriding hardcoded searches. |
| **4. Contact Discovery** | Fully implemented! Integrates SerpAPI to run Google Dorks (`site:linkedin.com target_domain editor`), extracting verified names and actual LinkedIn URLs directly from search snippets. |
| **5. Personalized Outreach** | Synthesizes BI insights and target crawled content to craft highly personalized emails. Generic templates are avoided. |
| **8. Editorial Content Gen** | Creates fully optimized, publication-ready markdown articles complete with headers and SEO metas. |
| **11. Real-time Dashboard** | Next.js dashboard visualizes the live LangGraph timeline and displays all metrics streaming via SSE. |
| **Bonus Features** | Multi-agent orchestration (LangGraph), Prospect memory (ChromaDB), Docker deployment. |

### 🟡 Mocked / Skipped Features (And Why)
| Feature | Why We Mocked It |
| :--- | :--- |
| **3. Opportunity Qualification (DA & Traffic)** | **Why Mock:** True metrics like Domain Authority (DA) or Organic Traffic are proprietary algorithms owned by Moz, Ahrefs, and Semrush. Accessing this data requires expensive, paid API keys. We simulate these metrics in the UI to show where the data *would* live, but use deterministic Keyword/Fit scoring under the hood. |
| **6. Outreach Automation (Sending Emails)** | **Why Mock:** The logic to send emails exists, but we simulate the final SMTP transport. Sending real automated emails requires verified domain records (SPF, DKIM, DMARC) and paid ESPs like SendGrid to avoid being blacklisted as spam. |
| **7. AI Reply Handling** | **Why Mock:** Setting up an Inbound Parse Webhook via SendGrid (or an IMAP listener) requires live DNS propagation and verified domains. Since this is an MVP without a live domain, we cannot catch real inbound replies. |
| **9. Backlink Placement** | **Why Mock:** The system generates the article, but automatically publishing it to a third-party site requires that site's CMS credentials (e.g., their WordPress Admin API keys). Without authorization, direct publishing is impossible. |
| **10. Backlink Verification** | **Why Mock:** Because we cannot physically place the backlink on third-party sites (see #9), we cannot run a crawler to verify its existence. The "Live Links" metric is simulated for UI demonstration purposes. |

---

## 🛠️ Setup Instructions

### Prerequisites
- Docker & Docker Compose
- API Keys for: Firecrawl, Tavily, SerpAPI, and your LLM (Gemini/OpenAI/Groq)

### Environment Variables
Create a `.env` file in the `backend/` directory:
```env
LLM_API_KEY="your-api-key"
TAVILY_API_KEY="your-api-key"
FIRECRAWL_API_KEY="your-api-key"
SERPAPI_API_KEY="your-api-key"
```

### Running Locally
```bash
docker-compose up --build
```
The UI will be instantly available at `http://localhost:3000`. The backend runs on `http://localhost:8000`.
