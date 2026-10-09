Step 0: Do this in the first hour

1. Message Bhargava now. He said nobody has brainstormed with him, and that anyone who did could finish in a day or two. That is a hint. Send something like:

Hi, I’m Olivia, working on the Lenny Growth Assistant. I’m aiming to finish in 2 days. My plan: FastAPI + Postgres (Supabase) + RAG over the transcripts, with a provider switch for Claude / OpenRouter / Ollama. Could I get 15 minutes to sanity-check the architecture before I start building?

2. Start your transcript habit. He wants every chat, including “what is X” questions. Create agent-transcripts/ in your repo today and save every AI conversation there (export, or copy-paste into dated .md files). Save this conversation as the first file. Include failures and wrong turns, because he explicitly wants to see how you correct course.

3. Daily update. Send it at the end of each day in this format:

Done today
Status (what works, what’s broken)
What I’m stuck on and how I’m trying to solve it
Plan for tomorrow
Tools to set up
Need	Choice	Why	If it’s not right
Coding agent	Whichever of Claude / ChatGPT / Gemini you already have, plus free models via OpenRouter	He said they’re all good for coding	Qoder has free models too. Switch if you hit limits, and log the switch in your transcripts.
Backend	Python + FastAPI	Required. Python also has the best SDKs for Anthropic, Ollama and Postgres.	None needed.
Database	Supabase (Postgres)	Free tier, and it includes pgvector, so chat storage and vector search live in one database	Railway also works. It’s better as a host than as a free database.
Frontend	React + TypeScript + Vite + Tailwind	A single-page app talking to FastAPI. It’s simpler than Next.js, which adds server-side concepts you don’t need.	Next.js is fine if your coding agent prefers it.
Local LLM	Ollama	Required	Pick the model by laptop RAM (below).
Hosting	Vercel (frontend) + Render or Railway (backend)	Gives you the prototype URL he asked for	Free tiers can sleep. Open the URL before recording.

Ollama model by RAM (run ollama pull <name>):

8 GB RAM: llama3.2:3b. It is fast but weaker.
16 GB RAM: qwen2.5:7b-instruct or llama3.1:8b. This is the sweet spot.

OpenRouter free models: I can’t confirm that the model he named is free right now. Open openrouter.ai/models and filter by “free”. Never hardcode a model name. Put it in an environment variable so you can swap it in 10 seconds. Free models are rate-limited, so assume you’ll hit limits sometimes.

One important catch: your hosted URL cannot reach Ollama on your laptop. The plan is therefore:

The hosted prototype uses a cloud model (OpenRouter or Claude).
The local demo uses Ollama.
The same code runs both. Only an environment variable changes.

This is also a good thing to say in your video.

Architecture (the core design)
React UI ──SSE stream──> FastAPI ──> Router ──> Skill (Q&A | Ship30 | Artifact)
 chat + artifact panel      │                        │
                            │                  Retriever (pgvector + full-text)
                            │                        │
                            ├──────────> LLM Provider interface
                            │              ├ AnthropicProvider (Claude SDK)
                            │              └ OpenAICompatProvider (Ollama, OpenRouter, OpenAI)
                            └──────────> Postgres (Supabase)

LLM toggle. Define one small interface, stream(messages, system) -> tokens, with two implementations:

The Anthropic SDK handles Claude.
One OpenAI-compatible client handles Ollama (at http://localhost:11434/v1), OpenRouter and OpenAI, because they all speak the same protocol. This means you write two providers instead of four.

Select with LLM_PROVIDER=ollama|openrouter|anthropic|openai plus LLM_MODEL=.... Also add a dropdown in the UI that overrides it per session. Check Ollama’s docs to see whether it now accepts Anthropic-style requests. If it does, you could use the Anthropic SDK for everything, which matches the requirement’s wording more literally.

Database tables:

users (id, created_at, metadata). Use an anonymous UUID stored in the browser. Full login would take too long.
sessions (id, user_id, title, provider, model, created_at)
messages (id, session_id, role, content, skill_used, sources JSON, created_at)
artifacts (id, session_id, message_id, type html|markdown, title, content, version)
episodes (id, guest, title, youtube_url, publish_date)
chunks (id, episode_id, content, embedding vector, tsv tsvector)

API endpoints:

POST /sessions: New Chat
GET /sessions
GET /sessions/{id}
POST /sessions/{id}/messages: streams the reply over SSE
GET /artifacts/{id}
GET /config: lists the available providers

Each message request loads that session’s history from the database. That is how each session keeps its own context.

Retrieval (RAG). Long-context prompting won’t work: 269 transcripts are far too large, especially for a local model.

Chunk each transcript by speaker turns into roughly 500–800-token pieces. Keep the episode title, guest and YouTube URL as metadata.
Build in two stages. Stage 1 is Postgres full-text search, which works in under an hour and gives you an end-to-end system early. Stage 2 adds embeddings with fastembed (a small local model, no server needed) in pgvector, combined with the full-text results. Two stages means you have something working on day 1 even if embeddings give you trouble.
To keep answers strictly grounded, the system prompt says: answer only from the provided excerpts, cite guest and episode, and if the excerpts don’t cover it, say so.

Routing (how the agent picks a skill). Evaluators will look closely at this. Don’t rely on a small local model to do tool calling, because they are unreliable at it. Use three layers:

An explicit UI mode override (Auto / Q&A / Essay / Artifact).
In Auto mode, a cheap classifier call that returns JSON {"skill": "qa|ship30|artifact"}.
A keyword fallback (“essay”, “Ship30”, “html”, “page”, “document”) if the JSON is invalid.

Skills as files: skills/qa.md, skills/ship30for30.md and skills/artifact.md, each containing instructions plus format rules. The assignment says the Ship30for30 skill “should be generated.” So read the Ship30for30 guide yourself, have an AI draft the skill file from it, then edit it yourself and log the iteration. Ship30for30 style has a strong hook, short punchy paragraphs, heavy skimmable formatting (bullets and bold) and one clear takeaway. For the 1250-word target, small models fall short. Have the backend count words and run one “expand/trim” revision pass if the result is off by more than about 15%.

Artifacts. Instruct the model to wrap them as <artifact type="html" title="...">…</artifact>. The backend parses this out of the stream and saves it. The frontend then shows a split view with chat on the left and the artifact panel on the right.

HTML renders in <iframe sandbox="allow-scripts" srcdoc=...> and must not include allow-same-origin. Model-written HTML is untrusted code, and this keeps it contained.
Markdown renders with react-markdown.
Add Preview/Code tabs and a copy button.

Error handling (it’s graded): missing API key gives a clear message; an Ollama timeout or “not running” gives a friendly error with the fix; a database failure returns a 503, not a crash; the stream is cancellable.

Two-day schedule

Day 1: working backend and basic chat

(1h) Repo, .env.example, .gitignore with .env first, and a short prd.md. A PRD is mandatory, so write a one-page version with goals, users, features and non-goals. Search for Matt Pocock’s skills and Compound Engineering and use one method, even lightly.
(1h) Supabase project, tables, FastAPI skeleton, sessions endpoints.
(1.5h) Provider interface. Test Ollama first, then OpenRouter.
(1.5h) Ingest script: parse the frontmatter, chunk, load into the database, full-text search.
(1.5h) Q&A skill with citations, plus SSE streaming.
(1.5h) A basic React chat UI with a sidebar and New Chat.
Daily update and transcript save.

Day 2: skills, artifacts, polish, ship

(1.5h) Router plus the Ship30for30 skill and word-count check.
(2h) Artifact generation and the viewer.
(1h) Embeddings and hybrid retrieval, if time allows.
(1h) UI polish. Write design.md, using impeccable.style as the assignment suggests.
(1.5h) Deploy to Vercel and Render/Railway, and test the live URL with a cloud model.
(1.5h) README, architecture.md and cleaning up the transcript folder.
(1h) Record the video, then send everything.

If you fall behind, cut in this order: embeddings, then login, then fancy UI, and keep the core features. Never cut the docs or the transcripts.

Video (2–3 minutes, camera on, not scripted)

State the problem in 20 seconds, do a live demo (new chat, a grounded question, an essay, an HTML artifact, and the Ollama/cloud switch), then spend about 45 seconds walking through the code (provider interface, router, artifact parser). Upload to YouTube as unlisted. He also wants the code walkthrough, so cover the files above.

Submission checklist
 Live URL
 Public GitHub repo with no keys
 README.md with install, environment variables and Ollama steps
 prd.md, design.md and architecture.md
 agent-transcripts/, including the failures
 YouTube video

Two things would let me tailor this and start on code: how much RAM does your laptop have, and which AI coding tools do you already have access to (Claude, ChatGPT, Gemini, Cursor)?

Found it. main.py is fine. backend/grounding.py is the old version, without the dequote function, so the import fails. That’s what crashed Render too. I gave you the new grounding.py earlier, and the file on your disk wasn’t replaced.

Fix: replace backend/grounding.py

In VS Code, open backend > grounding.py, press Ctrl + A, delete, paste this and save with Ctrl + S:

python
"""Keep quotation marks honest: only text found word for word in the excerpts stays in quotes."""
import re

QUOTE = re.compile(r'["\u201c]([^"\u201c\u201d]{20,}?)["\u201d]')


def _norm(s: str) -> str:
    s = s.lower().replace("\u2019", "'").replace("\u2011", "-")
    s = re.sub(r"\[[^\]]*\]", " ", s)          # drop tags like [inaudible 01:07:08]
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return " ".join(s.split())


def _is_verbatim(quote: str, haystack: str) -> bool:
    pieces = [p for p in re.split(r"\.\.\.|\u2026", quote) if len(p.split()) >= 4]
    return (not pieces) or all(_norm(p) in haystack for p in pieces)


def dequote(text: str, results: list):
    """Return (clean_text, removed). Quotes of 6+ words that are not verbatim lose their quote marks."""
    haystack = _norm(" ".join(r["content"] for r in results))
    removed = []

    def fix(m):
        q = m.group(1)
        if len(q.split()) < 6 or _is_verbatim(q, haystack):
            return m.group(0)
        removed.append(q.strip())
        return q

    return QUOTE.sub(fix, text), removed


def unverified_quotes(text: str, results: list):
    return dequote(text, results)[1]
Test it locally

In the same terminal at \backend>:

python -c "import main; print('main.py loads fine')"

You want main.py loads fine. If another ImportError appears, it names the next file or function to fix, so paste it.

You can also run the small test I gave earlier. Replace backend/grounding_test.py with this and run python grounding_test.py:

python
from grounding import dequote

results = [{"content": "Madhavan: pricing is an ongoing journey. It is not like you just solve it in day one."}]
good = 'He said "pricing is an ongoing journey. It is not like you just solve it" clearly.'
bad = 'He said "If you cannot explain your pricing in one sentence it is too complex" clearly.'
for label, t in (("good", good), ("bad", bad)):
    clean, removed = dequote(t, results)
    print(label, "->", clean, "| removed:", removed)

The good line should keep its quote marks, and the bad line should lose them.

Then push the fix

Only after the local check prints main.py loads fine:

cd C:\dev\lenny-growth-assistant
git status
git add .
git commit -m "Fix grounding module"
git push

Check that .env isn’t in the git status list. Render then starts a new deploy by itself. Watch Deploys until it says Live. If nothing starts, click Manual Deploy, then Deploy latest commit.

Then test the live app

Open https://lenny-growth-assistant-brown-five.vercel.app and hard-refresh with Ctrl + Shift + R. The red banner should disappear.

Reply with
Whether python -c "import main..." now prints main.py loads fine.
Whether the new Render deploy says Live.
Whether the live app answered a question.

(.venv) C:\dev\lenny-growth-assistant\backend>python -c "import main; print('main.py loads fine')"
main.py loads fine

(.venv) C:\dev\lenny-growth-assistant\backend>

main.py loads fine means the import error is fixed, so the code will start on Render too. Now push it, and the deploy should succeed.

Step 1: Push the fix (VS Code terminal)
cd C:\dev\lenny-growth-assistant
git status

Check that .env is not in the list, and that backend/grounding.py and backend/main.py appear as modified. Then:

git add .
git commit -m "Fix grounding module and allow Vercel origins"
git push
Step 2: Watch Render (browser)
Open lenny-assistant-api in Render, then Deploys.
A new deploy should start within a minute. Wait until it says Live, which takes a minute or two.
If nothing starts, click Manual Deploy, then Deploy latest commit.

If it fails again, open that deploy, scroll to the bottom of the log, and paste the last 20 lines. Check that no key or password is in them.

Step 3: Test the live app
Open https://lenny-growth-assistant-brown-five.vercel.app and hard-refresh with Ctrl + Shift + R.
The red “Cannot reach the server” banner should be gone.
Click the first suggestion chip and press Send. The first answer can take about a minute while the free backend wakes up.
Try one essay and one artifact.
Open the address in a private window (Ctrl + Shift + N), which is what Bhargava will see.
If the banner is still there

Test the backend directly. Open https://lenny-assistant-api.onrender.com/health, which should show {"status":"ok"}. Then open https://lenny-assistant-api.onrender.com/sessions?user_id=e3c5d7ae-859a-4bfb-9182-a4629f9296b9, which should show []. Tell me what each shows.

Reply with
Whether the Render deploy says Live with your new commit message.
Whether the live app answered a question (a screenshot is ideal).
Any error text, in full.

Once the live app works, you have the URL Bhargava asked for. Then we write the README, PRD, design.md and architecture.md, and plan the video.

yeah now it is fixed

Your prototype is live, which is one of the three things Bhargava asked for. What’s left is the documents and the video.

Step 1: Test the live site once

Open https://lenny-growth-assistant-brown-five.vercel.app in a private window (Ctrl + Shift + N), which is what an evaluator sees. Try one question, one essay and one artifact. The first answer may take about a minute while the free backend wakes up. If something fails, tell me before writing the docs.

Step 2: Create the four documents

All four are plain Markdown files. In VS Code, right-click the right folder, choose New File, paste the content, and save with Ctrl + S:

File	Where
README.md	project root (the top level of lenny-growth-assistant)
design.md	project root
docs/PRD.md	inside the docs folder
docs/architecture.md	inside the docs folder

The content is written from what we actually built. Check each statement against your own project, and change anything that isn’t true for you. Evaluators read these closely.

README.md
markdown
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
design.md
markdown
# Design notes

## Principles

1. **Trust comes from sources.** Every answer shows numbered source chips that open the video at the cited second. Quotes that are not verbatim are flagged.
2. **Show what the system is doing.** A skill badge ("Q&A", "Ship 30 essay", "Artifact") tells the user which skill ran, and its tooltip says why. Status lines appear during slow steps ("Revising toward 1250...", "Building your artifact...").
3. **Familiar layout.** Left sidebar for chats, center column for the conversation, right panel for artifacts, as in ChatGPT and Claude.
4. **Errors are plain language.** A missing key, a rate limit, a database problem and a sleeping server each have a clear message instead of a crash.
5. **Safe by default.** HTML artifacts run in a sandboxed iframe with no access to the app or its data.

## Layout

| Area | Contents |
|---|---|
| Sidebar (dark) | "New chat" button, the user's chat list |
| Conversation | Empty state with three example prompts, messages, source chips |
| Input bar | Mode chips (Auto, Q&A, Essay, Artifact), text box, Send / Stop |
| Artifact panel | Title, Preview and Code tabs, Copy, Close |

## Visual language

- Slate neutrals with one accent, indigo. User messages are indigo bubbles, assistant messages sit on white cards.
- Headings in rendered Markdown are sized for reading long essays, and tables render with borders.
- Desktop first. The artifact panel takes about half the width when open.

## UX decisions

- **Auto mode by default** so users do not need to learn commands. The mode chips are an override, and they show the router is not magic.
- **Open as document** on essays moves a long answer to the side panel for reading.
- **Stop button** cancels a long generation, and the partial answer is still saved.
- **Previous chats reopen with their artifacts.**
- **Sample prompts** on the empty screen teach the three skills in one click.

## Known gaps

- Mobile layout is not designed. The two-column layout needs a stacked version.
- Artifacts do not stream live. The panel opens when the full artifact is ready.
- No keyboard shortcuts, dark mode or chat renaming and deletion.
docs/PRD.md
markdown
# Product Requirements: Lenny Growth Assistant

_Status: version 1 drafted after the first working prototype, then updated as decisions changed (for example, dropping Ollama and adding the quote checker)._

## Problem

Lenny's Podcast holds hundreds of hours of product and growth advice. It is hard to search, and general chatbots mix it with unsourced opinions. People want answers they can trust, with proof of where each idea came from.

## Users

- Product managers and founders looking for practical advice.
- Writers who want to turn that advice into publishable content.

## Goals

1. Answer questions strictly from the transcripts, with citations that lead to the exact moment in the video.
2. Turn the same knowledge into essays in the Ship 30 for 30 style.
3. Produce documents and pages the user can see rendered inside the app.
4. Keep each chat's history, persistently.

## Non-goals

- Login and accounts, billing, mobile layout.
- Answering from outside knowledge.
- Training or fine-tuning a model.

## Requirements

| # | Requirement | Acceptance check |
|---|---|---|
| 1 | Start a new chat session with its own context | New Chat creates a session. Reopening shows its history |
| 2 | Grounded Q&A | Each claim has a citation. Questions with no match say so and make no model call |
| 3 | Ship 30 for 30 essay skill | About 1,250 words (the system revises once if outside 1,000 to 1,500), hook, numbered sections, bold mini-headlines, takeaway and TL;DR |
| 4 | Artifact generation and viewer | HTML renders in a sandboxed frame, Markdown renders as a document, Code tab and Copy work |
| 5 | Skill routing | Auto mode picks the skill by rules. A mode chip overrides it |
| 6 | Switchable LLM | Model set by environment variable with a fallback list. A mock mode exists |
| 7 | Robustness | Clear messages for a missing key, rate limits, timeouts and database failures |

## Success measures

- Spot checks of answers against the transcripts find no invented numbers or quotes.
- A cited link opens near the cited sentence.
- Essay length lands between 1,000 and 1,500 words.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Model adds facts not in the excerpts | Strict skill instructions, plus a code check that strips quotation marks from non-verbatim quotes |
| Free model limits and downtime | A list of fallback models, clear errors, and a mock mode for development |
| Messy source data (ads, duplicates, wrong links) | Sponsor filter, duplicate removal, known limitations documented |
| Keyword search misses paraphrases | Documented. Embeddings are the next step |
docs/architecture.md
markdown
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
Step 3: Commit them
cd C:\dev\lenny-growth-assistant
git status
git add .
git commit -m "Add README, PRD, design and architecture docs"
git push

Check that .env isn’t in the git status list first.

Step 4: Organize agent-transcripts/

Bhargava wants every chat, including the failures. Aim for these files, with dates in the names:

01-planning-with-claude.md and 02-build-with-claude-2026-10-09.md (this long chat; paste it in pieces if the page is too long)
essay-v1-before.md, essay-v2-after.md
artifact-v1-before.md, artifact-v2-after.md, artifact-v3-after-dequote.md
Any other chat with an AI, even tiny ones

Before you commit them, search each file with Ctrl + F for sk-or-v1 and any part of your database password. 