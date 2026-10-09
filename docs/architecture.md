# Architecture

## Components

| Part | Technology | Role |
|---|---|---|
| Frontend | React, TypeScript, Vite, Tailwind | Chat UI, mode selector, artifact viewer |
| Backend | FastAPI (Python) | Sessions, routing, retrieval, streaming |
| Database | Supabase Postgres | Chats, artifacts, transcript chunks |
| LLM | OpenRouter (OpenAI-compatible API) | Generates answers |
| Hosting | Vercel (frontend), Render (backend) | Public deployment |

## Request flow

1. The browser calls `POST /sessions/{id}/messages` with the text and a mode.
2. The backend saves the user message, then `router.py` picks a skill.
3. `retrieval.py` finds excerpts (6 for Q&A, 10 for essays, 8 for artifacts). Artifact follow-ups reuse the conversation instead.
4. `prompts.py` builds the prompt from `skills/<skill>.md`, the excerpts and recent history.
5. `llm.py` streams the model reply. The backend forwards it as Server-Sent Events.
6. Post-processing: essay word count and one revision, quote checking, artifact extraction.
7. The reply, sources and artifact are saved.

## Agentic routing logic

1. If the user chose a mode, use it.
2. A build verb plus a strong artifact word (html, landing page, dashboard...) routes to **artifact**.
3. "essay", "Ship 30" or "write an article" routes to **ship30for30**.
4. A build verb plus a soft artifact word (markdown, checklist, one-pager...) routes to **artifact**.
5. Everything else routes to **qa**.

This costs no model calls. `router_test.py` documents the behavior. An LLM classifier is a possible later addition.

## Skills

Skills are Markdown files in `backend/skills/` that define the role, grounding rules and output format. The Ship 30 for 30 skill was drafted with an AI from the Ship 30 for 30 guide (headline promise, 1/3/1 rhythm, wheels and spokes, tequila test), then reviewed and edited. The drafts and revisions are in `agent-transcripts/`.

## Database schema

| Table | Key columns |
|---|---|
| `users` | id (uuid), created_at, metadata |
| `sessions` | id, user_id, title, model, created_at, updated_at |
| `messages` | id, session_id, role, content, skill_used, sources (jsonb), created_at |
| `artifacts` | id, session_id, message_id, type (html or markdown), title, content, version |
| `episodes` | id, slug, guest, title, youtube_url, publish_date |
| `chunks` | id, episode_id, chunk_index, start_seconds, speaker, content, embedding (vector), tsv (generated full-text column) |

Deleting a session cascades to its messages and artifacts.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health`, `GET /config` | Liveness, and the active provider and model |
| `POST /sessions` | New chat |
| `GET /sessions?user_id=` | Chat list |
| `GET /sessions/{id}` | History with artifacts |
| `POST /sessions/{id}/messages` | Send a message and stream the reply |

### Stream events

`skill`, `sources`, `token`, `status`, `replace`, `meta`, `check`, `artifact`, `error`, `done`.

## Retrieval

Transcripts are parsed per speaker turn, cleaned (inaudible tags, sponsor reads) and grouped into chunks of about 2,400 characters that keep their start time. Search uses Postgres full-text search. Words that appear in more than 10% of chunks are dropped, and results are limited to two per guest.

## LLM switch

`llm.py` exposes `stream_chat()`. `LLM_PROVIDER` selects `openrouter` or `mock`. `LLM_MODEL` takes a comma-separated list, and the next model is tried when one fails before sending any text. Errors are converted into clear messages.

## Error handling

| Case | Behavior |
|---|---|
| Missing API key | Message naming the variable to set |
| Rate limit or model outage | Next model tried, then a clear message |
| Database failure before streaming | HTTP 503 with a friendly message |
| Database failure during streaming | `error` event |
| No matching excerpts | Says so, makes no model call |
| User presses Stop | The partial answer is saved |

## Deployment

Vercel builds `frontend/` with `VITE_API_URL`. Render runs `uvicorn main:app --host 0.0.0.0 --port $PORT` from `backend/`, with secrets in its environment settings. CORS allows localhost, `FRONTEND_ORIGIN` and `*.vercel.app`.