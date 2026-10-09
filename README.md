# Lenny Growth Assistant

An AI chat app that answers product and growth questions **only from Lenny's Podcast transcripts**, writes **Ship 30 for 30 style essays**, and builds **HTML / Markdown artifacts** that render beside the chat.

- **Live app:** https://lenny-growth-assistant-brown-five.vercel.app
- **API (docs):** https://lenny-assistant-api.onrender.com/docs
- **Video walkthrough:** _add your YouTube link here_

> The free Render backend sleeps after about 15 minutes of inactivity. The first request can take around a minute.

## What it does

| Skill | Trigger | Output |
|---|---|---|
| Q&A | Default | A short answer with `[n]` citations and source chips that open the YouTube video at the cited moment |
| Ship 30 for 30 essay | "essay", "Ship 30" or the Essay mode | A markdown essay of about 1,250 words with a hook, numbered sections, bold mini-headlines and a TL;DR |
| Artifact | A build request ("make a landing page", "create a checklist") or the Artifact mode | A Markdown document or a self-contained HTML page in a side panel (Preview, Code, Copy) |

Each chat session keeps its own history in Postgres. A mode selector (Auto, Q&A, Essay, Artifact) lets the user override the router.

## Architecture in brief

```
React (Vite, Tailwind)  --SSE-->  FastAPI  --> router --> skill (qa | ship30for30 | artifact)
  chat + artifact panel               |                         |
                                      |                  retrieval (Postgres full-text search)
                                      |                         |
                                      +-----> llm.py ---> OpenRouter (OpenAI-compatible API)
                                      +-----> Supabase Postgres (sessions, messages, artifacts, chunks)
```

Full details are in [docs/architecture.md](docs/architecture.md). The product thinking is in [docs/PRD.md](docs/PRD.md) and [design.md](design.md).

## Run it locally

Requirements: Python 3.12, Node 20+, a free [Supabase](https://supabase.com) project and an [OpenRouter](https://openrouter.ai) API key.

1. **Clone and get the transcripts**
```
   git clone https://github.com/OliviaZaxiyo/lenny-growth-assistant.git
   cd lenny-growth-assistant
   git clone https://github.com/ChatPRD/lennys-podcast-transcripts data/lennys-podcast-transcripts
```
2. **Supabase:** create a project, then enable the `vector` extension (Database, Extensions). Copy the **Session pooler** connection string (Connect, Direct, Session pooler).
3. **Backend**
```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   copy .env.example .env          # macOS/Linux: cp .env.example .env
```
   Edit `.env` (see the table below), then:
```
   python init_db.py               # creates the tables
   python ingest.py                # parses, cleans, chunks and loads the transcripts (a few minutes)
   python remove_dupes.py          # removes 7 exact duplicate episodes found in the dataset
   uvicorn main:app --reload
```
4. **Frontend** (new terminal)
```
   cd frontend
   npm install
   npm run dev
```
   Open http://localhost:5173.

### Environment variables

| Variable | Where | Meaning |
|---|---|---|
| `DATABASE_URL` | backend | Supabase Session pooler connection string |
| `OPENROUTER_API_KEY` | backend | Your OpenRouter key |
| `LLM_PROVIDER` | backend | `openrouter` (real model) or `mock` (fake streamed text, costs nothing, for UI work) |
| `LLM_MODEL` | backend | One OpenRouter model id, or several separated by commas. They are tried in order |
| `FRONTEND_ORIGIN` | backend | Your frontend address, for CORS (optional locally) |
| `VITE_API_URL` | frontend | Backend address (defaults to http://127.0.0.1:8000) |

Never commit `.env`. Only the `.env.example` files with placeholders are in the repo.

### Switching the LLM

Change `LLM_MODEL` in `backend/.env` and restart the backend. `GET /config` shows the active provider and model. `LLM_PROVIDER=mock` runs the whole app without any model request.

## Useful scripts (in `backend/`)

| Script | Purpose |
|---|---|
| `retrieval.py "question"` | See which excerpts the search returns |
| `router_test.py` | Shows which skill each sample message routes to |
| `grounding_test.py` | Tests the quote checker |
| `chat_test.py [mode] question` | Calls the streaming endpoint from the terminal |
| `grep_transcripts.py word guest` | Search the raw transcripts to verify a claim |

## Grounding and quality checks

- Answers use only retrieved excerpts, and every claim carries a numbered citation.
- Each citation links to the YouTube video at the exact second of the excerpt.
- **Quote checker:** in code, any quotation of 6+ words that is not word for word in the excerpts has its quotation marks removed, and the UI shows which passages were paraphrases.
- Sponsor ads are filtered out of the transcripts, and 7 duplicate episode files were removed.

## Known limitations

- **Keyword search, not embeddings.** Wording mismatches (for example "three to 5%" versus "percent") can be missed. A pgvector column is in the schema for a future semantic search.
- A follow-up question is searched on its own text. Artifact requests reuse the earlier conversation and the current artifact instead.
- Free OpenRouter models vary in quality and speed and have daily limits. The app tries several models and shows clear errors for rate limits.
- Some transcript metadata is unreliable. A few episodes share a YouTube link, so a source link can open the wrong video.
- The quote checker covers Markdown and chat text, not HTML artifacts.
- No login: a random ID stored in the browser separates users.
- Per the reviewer's instruction, the project runs on a cloud model through OpenRouter and does not use Ollama. The LLM layer in `llm.py` is a small interface, so another provider can be added.
- The backend uses the OpenAI Python SDK against OpenRouter's compatible endpoint, not the Anthropic SDK.

## Repository layout

```
backend/    FastAPI app, skills/, retrieval, ingestion, tests
frontend/   React app
docs/       PRD and architecture
agent-transcripts/   Every AI chat used while building, including the wrong turns
```