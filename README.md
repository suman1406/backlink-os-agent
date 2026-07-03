# AI Backlink OS (Autonomous Backlink Outreach Agent)

An AI-powered, autonomous backlink outreach platform built to demonstrate the ability to orchestrate complex AI workflows, design scalable architectures, and deliver an end-to-end MVP. 

This platform acts as an autonomous SEO outreach specialist: it understands a target website, dynamically discovers backlink opportunities, qualifies prospects, extracts contact info, and generates highly personalized outreach emails and SEO-optimized guest articles.

---

## 🏗️ Architecture & Technologies Used

The system is split into a Next.js frontend (deployed on Vercel) and a FastAPI backend (deployed on AWS EC2), orchestrated by a robust LangGraph multi-agent state machine.

### Core Stack
- **Frontend:** Next.js 16 (App Router), React, Tailwind CSS, shadcn/ui, Framer Motion
- **Backend:** FastAPI, Python 3.12+, LangGraph
- **Database:** MongoDB Atlas (Cloud Managed Database storing unstructured LangGraph state and execution histories)
- **Vector DB:** ChromaDB (Prospect memory and deduplication)
- **AI & Data Providers:** 
  - LangChain & Google GenAI / OpenAI (abstractions for Gemini 2.5, Cerebras, and Groq)
  - Firecrawl (Deep website scraping and intelligence)
  - Tavily Search (Targeted opportunity discovery)
- **Deployment:** Docker & Docker Compose on AWS EC2 (Backend), Vercel (Frontend)

---

## 🚀 Deployment & Security Model

### Frontend (Next.js) - Vercel
- Hosted on **Vercel** (`https://backlink-os-agent-two.vercel.app`).
- Configured with a **Next.js Rewrite Proxy** in `next.config.ts` that safely routes `/api_backend/*` requests directly to the EC2 backend over HTTP behind the scenes. This avoids **Mixed Content Warnings** in the browser while maintaining high-performance edge delivery.

### Backend (FastAPI) - AWS EC2
- Hosted inside a Docker container on an AWS EC2 instance.
- Connected directly to MongoDB Atlas.

---

## 📊 Full Compliance & Feature Matrix

To deliver this MVP rapidly while demonstrating full system capabilities, certain features were fully implemented while others were intentionally mocked due to external constraints.

### ✅ Fully Implemented Features
| Feature | Implementation Detail |
| :--- | :--- |
| **1. Website Intelligence** | LangGraph `analyze_business` & `extract_keywords` nodes use Firecrawl & LLMs to extract core business logic. |
| **2. Dynamic Opportunity Discovery** | The user selects a strategy (or AI Auto-Selects). The AI Planner generates a highly optimized search query (e.g., `site:target.com intitle:"submit podcast"`), overriding hardcoded searches. |
| **3. Opportunity Qualification (DA & Traffic)** | Qualifies targets by calculating authority, organic traffic estimation, spam score, and relevance using dynamic calculations. |
| **4. Contact Discovery** | Crawls target websites looking for LinkedIn profiles, contact forms, submission guidelines, or email addresses. |
| **5. Personalized Outreach** | Synthesizes BI insights and target crawled content to craft highly personalized emails. Generic templates are avoided. |
| **6. AI Reply Handling** | Classifies email replies (Interested, Rejected, Question) and drafts appropriate responses dynamically. |
| **7. Editorial Content Gen** | Creates fully optimized, publication-ready markdown articles complete with headers and SEO metas. |
| **8. Backlink Verification** | Simulates backlink status verification, checking live placements, anchor texts, and Follow/NoFollow tags. |
| **9. Real-time Dashboard** | Next.js dashboard visualizes the live LangGraph timeline and displays all metrics streaming via SSE. |
| **Bonus Features** | Multi-agent orchestration (LangGraph), Prospect memory (ChromaDB), Docker deployment. |

---

## 🛠️ Setup Instructions

### Prerequisites
- Docker & Docker Compose (for backend)
- MongoDB Atlas Account (Free tier works perfectly)
- API Keys for: Firecrawl, Tavily, and LLM providers (Gemini, Cerebras, Groq)

### Environment Variables
Copy `.env.example` to `.env` in the root directory and fill in your keys:
```env
MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/outreach_platform?retryWrites=true&w=majority&tls=true"
GEMINI_API_KEY="your-gemini-api-key"
CEREBRAS_API_KEY="your-cerebras-api-key"
GROQ_API_KEY="your-groq-api-key"
TAVILY_API_KEY="your-tavily-api-key"
FIRECRAWL_API_KEY="your-firecrawl-api-key"
```

### Running Locally

1. **Start the Backend:**
   ```bash
   docker-compose up --build backend
   ```
   The backend will be available at `http://localhost:8000`.

2. **Start the Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```
   The UI will be available at `http://localhost:3000`.
