# AI Newsroom Platform

Production-grade autonomous newsroom powered by LangGraph multi-agent AI.

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `NEWSAPI_KEY` — from newsapi.org (free tier works)
- `META_APP_ID` / `META_APP_SECRET` — from Facebook Developer Console
- `UNSPLASH_ACCESS_KEY` — from unsplash.com/developers (optional)
- `GOOGLE_CSE_API_KEY` / `GOOGLE_CSE_ID` — from console.cloud.google.com (optional)

### 2. Start all services

```bash
docker compose up --build
```

Services:
- **Backend API**: http://localhost:8080 (docs at /docs)
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Create your first user

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword","full_name":"Your Name"}'
```

### 5. Use the platform

1. Open http://localhost:3000
2. Enter a news topic (e.g. "AI regulation EU policy")
3. Click "Run Pipeline" — watch agents work in real time
4. Review the generated story in the center panel
5. Check confidence score and verification status
6. Approve or reject in the right panel
7. For approved stories: select platforms and publish

## Architecture

```
NewsroomState (LangGraph)
    ↓
Discovery Agent → RSS + NewsAPI + Playwright
    ↓
Verification Agent → cross-source + confidence scoring
    ↓ (< 0.35 confidence → auto-reject)
Summarization Agent → Claude claude-sonnet-4-6 structured output
    ↓
Media Agent → Unsplash + Google CSE + Pillow social cards
    ↓
[interrupt_before] Human Approval Node
    ↓ (editor approves)
Publishing Agent → Celery → Meta Graph API (Facebook + Instagram)
```

## Phase Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Complete | Discovery + Verification + SSE streaming |
| 2 | ✅ Complete | Summarization + Media + Frontend scaffold |
| 3 | Next | Human approval UI + WebSocket |
| 4 | Next | Meta publishing + OAuth flow |
| 5 | Future | Playwright scraping + GDELT + monitoring |
