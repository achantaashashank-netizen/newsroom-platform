# AI Newsroom Platform

An autonomous newsroom powered by a LangGraph multi-agent pipeline. Given a topic, it discovers articles from 36+ RSS feeds, NewsAPI, GDELT, and Hacker News — verifies them across sources, writes a full story with Claude, generates media, and publishes to Facebook and Instagram.

## Demo

> Enter a topic → watch 5 agents run in real time via SSE streaming → review + approve → publish

---

## Architecture

```
Query
  ↓
Discovery Agent
  ├── 36 RSS feeds (Reuters, AP, BBC, NYT, Guardian, Al Jazeera, France24, NHK, ...)
  ├── NewsAPI
  ├── GDELT (global event detection)
  └── Hacker News (Algolia API)
  ↓
Verification Agent
  ├── Per-source domain reliability scores
  ├── Cross-source corroboration (keyword overlap)
  ├── Fake news flagging (known bad domains, single-source detection)
  └── Confidence score = corroboration × 0.6 + reliability × 0.4
  ↓  (< 0.35 confidence → auto-reject)
Summarization Agent  (Claude Sonnet)
  ├── Headline, sub-headline, 2-3 paragraph summary
  ├── 5 bullet points, hashtags, Facebook + Instagram captions
  └── SEO analysis (focus keyword, meta description, slug, readability)
  ↓
Media Agent
  ├── DALL-E cartoon generation
  ├── Hugging Face FLUX fallback
  ├── Pollinations.ai fallback
  └── Social cards (Facebook 1200×630, Instagram 1080×1080)
  ↓
Human Approval  (LangGraph interrupt point)
  ↓  (editor approves in UI)
Publishing Agent  →  Celery  →  Meta Graph API (Facebook + Instagram)
```

---

## Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph + LangChain Anthropic |
| LLM | Claude Sonnet (summarization) + Claude Haiku (SEO) |
| Backend | FastAPI + Python 3.12 |
| Task queue | Celery + Redis |
| Database | PostgreSQL + SQLAlchemy async + Alembic |
| Frontend | Next.js 14 + Tailwind CSS |
| Media | OpenAI DALL-E / Hugging Face FLUX / Pollinations |
| Publishing | Meta Graph API (Facebook + Instagram) |
| Infrastructure | Docker Compose |

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/achantaashashank-netizen/newsroom-platform.git
cd newsroom-platform
cp .env.example .env
```

Fill in `.env`:

| Variable | Source | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com | Yes |
| `NEWSAPI_KEY` | newsapi.org (free tier) | Recommended |
| `OPENAI_API_KEY` | platform.openai.com | Optional (image gen) |
| `HF_TOKEN` | huggingface.co | Optional (image gen fallback) |
| `META_APP_ID` / `META_APP_SECRET` | Facebook Developer Console | Optional (publishing) |
| `GOOGLE_CSE_API_KEY` / `GOOGLE_CSE_ID` | console.cloud.google.com | Optional (image search) |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers | Optional (image search) |

GDELT and Hacker News require no API key.

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8080 |
| API Docs (Swagger) | http://localhost:8080/docs |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Register a user

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword","full_name":"Your Name"}'
```

### 5. Run the pipeline

1. Open http://localhost:3000 and log in
2. Enter a news topic — e.g. `"EU AI Act enforcement"` or `"Fed interest rate decision"`
3. Click **Run Pipeline** — watch all 5 agents run live via SSE streaming
4. Review the generated story, confidence score, and source breakdown
5. Approve or reject in the right panel
6. For approved stories: select platforms and publish to Meta

---

## News Sources

**RSS Feeds (36 total)**

| Category | Outlets |
|---|---|
| Wire services | Reuters, AP News, BBC World |
| US news | NPR, NY Times, Washington Post, Guardian, USA Today, PBS NewsHour, NBC News, CBS News, LA Times |
| Business / Finance | Bloomberg, Financial Times, CNBC, Forbes, Wall Street Journal, The Economist |
| Tech | TechCrunch, Ars Technica, Wired, The Verge, MIT Technology Review |
| Politics | Politico, The Hill |
| Science / Health | Science Daily, Nature, New Scientist, Live Science |
| Environment | Guardian Environment, Inside Climate News |
| International | Al Jazeera, Deutsche Welle, France24, CBC Canada, ABC Australia, Euronews, South China Morning Post, Times of India, NHK World, RFI English |

**APIs**
- **NewsAPI** — keyword search across 80,000+ sources
- **GDELT** — global event detection, last 24h coverage
- **Hacker News** — Algolia API, tech/startup stories with traction

All sources run in parallel via `asyncio.gather`.

---

## Project Structure

```
newsroom-platform/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph nodes (discovery, verification, summarization, media, publishing)
│   │   ├── tools/           # RSS, NewsAPI, GDELT, Hacker News, image tools, source reliability DB
│   │   ├── routers/         # FastAPI endpoints (stories, auth, social accounts)
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Story service (DB persistence)
│   │   └── workers/         # Celery tasks (discovery, publishing)
│   ├── alembic/             # DB migrations
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages
│       ├── components/      # UI components (pipeline view, story card, trending panel)
│       └── lib/             # API client
├── docker-compose.yml
└── .env.example
```

---

## Environment Variables

See `.env.example` for the full list with descriptions.
