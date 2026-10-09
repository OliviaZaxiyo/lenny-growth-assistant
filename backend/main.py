"""FastAPI app: sessions, history, skill routing and the streaming chat endpoint."""
import json
import logging
import os
from typing import Literal
from uuid import UUID

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from artifacts import extract_artifact
from db import connect
from grounding import unverified_quotes
from llm import LLMError, current_config, stream_chat
from prompts import build_messages, revision_messages
from retrieval import search
from router import choose_skill

load_dotenv()
log = logging.getLogger("app")

app = FastAPI(title="Lenny Growth Assistant")

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.getenv("FRONTEND_ORIGIN"):
    origins.append(os.getenv("FRONTEND_ORIGIN"))
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

NO_ANSWER = ("I couldn't find anything in the podcast transcripts that matches that question. "
             "Try rephrasing it or using more specific terms.")
ESSAY_TARGET, ESSAY_MIN, ESSAY_MAX = 1250, 1000, 1500
EXCERPTS_PER_SKILL = {"qa": 6, "ship30for30": 10, "artifact": 8}


@app.exception_handler(psycopg.Error)
async def db_error_handler(request, exc):
    log.exception("Database error")
    return JSONResponse(status_code=503,
                        content={"detail": "The database is unavailable. Please try again shortly."})


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


class NewSession(BaseModel):
    user_id: UUID


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    mode: Literal["auto", "qa", "essay", "artifact"] = "auto"


@app.get("/")
def root():
    return {"app": "Lenny Growth Assistant API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config")
def config():
    return current_config()


@app.post("/sessions")
def create_session(body: NewSession):
    with connect() as conn:
        conn.execute("insert into users (id) values (%s) on conflict (id) do nothing", (body.user_id,))
        row = conn.execute(
            "insert into sessions (user_id, model) values (%s, %s) returning id, title, created_at",
            (body.user_id, current_config()["model"]),
        ).fetchone()
    return row


@app.get("/sessions")
def list_sessions(user_id: UUID):
    with connect() as conn:
        return conn.execute(
            "select id, title, created_at, updated_at from sessions "
            "where user_id = %s order by updated_at desc",
            (user_id,),
        ).fetchall()


@app.get("/sessions/{session_id}")
def get_session(session_id: UUID):
    with connect() as conn:
        s = conn.execute("select id, title, created_at from sessions where id = %s", (session_id,)).fetchone()
        if not s:
            raise HTTPException(404, "Session not found")
        msgs = conn.execute(
            "select id, role, content, skill_used, sources, created_at from messages "
            "where session_id = %s order by created_at",
            (session_id,),
        ).fetchall()
        arts = conn.execute(
            "select id, message_id, type, title, content, version from artifacts "
            "where session_id = %s order by created_at",
            (session_id,),
        ).fetchall()
    return {**s, "messages": msgs, "artifacts": arts}


def sse(kind: str, **data) -> str:
    return f"data: {json.dumps({'type': kind, **data})}\n\n"


def save_assistant(session_id, text, sources, skill):
    with connect() as conn:
        row = conn.execute(
            "insert into messages (session_id, role, content, skill_used, sources) "
            "values (%s, 'assistant', %s, %s, %s) returning id",
            (session_id, text, skill, Jsonb(sources)),
        ).fetchone()
        conn.execute("update sessions set updated_at = now() where id = %s", (session_id,))
    return row["id"]


def save_artifact(session_id, message_id, art):
    with connect() as conn:
        conn.execute(
            "insert into artifacts (id, session_id, message_id, type, title, content, version) "
            "values (%s, %s, %s, %s, %s, %s, %s)",
            (art["id"], session_id, message_id, art["type"], art["title"], art["content"], art["version"]),
        )


@app.post("/sessions/{session_id}/messages")
def send_message(session_id: UUID, body: MessageIn):
    question = body.content.strip()

    # Database work happens BEFORE streaming starts, so a failure is a clean 503.
    with connect() as conn:
        s = conn.execute("select id, title from sessions where id = %s", (session_id,)).fetchone()
        if not s:
            raise HTTPException(404, "Session not found")
        history = conn.execute(
            "select role, content from messages where session_id = %s "
            "and role in ('user', 'assistant') order by created_at desc limit 10",
            (session_id,),
        ).fetchall()[::-1]
        latest = conn.execute(
            "select type, title, content from artifacts where session_id = %s "
            "order by created_at desc limit 1",
            (session_id,),
        ).fetchone()
        n_art = conn.execute(
            "select count(*) as n from artifacts where session_id = %s", (session_id,)
        ).fetchone()["n"]
        conn.execute(
            "insert into messages (session_id, role, content) values (%s, 'user', %s)",
            (session_id, question),
        )
        if s["title"] == "New chat":
            conn.execute("update sessions set title = %s where id = %s", (question[:60], session_id))

    skill, reason = choose_skill(question, body.mode)
    has_context = skill == "artifact" and (bool(latest) or any(m["role"] == "assistant" for m in history))

    def generate():
        reply, sources, artifact = "", [], None
        try:
            yield sse("skill", skill=skill, reason=reason)

            results = []
            if not has_context:
                results, _used = search(question, k=EXCERPTS_PER_SKILL[skill])
            sources = [{"n": i, "guest": r["guest"], "title": r["title"], "url": r["url"]}
                       for i, r in enumerate(results, start=1)]
            yield sse("sources", sources=sources)

            if not results and not has_context:
                # Nothing to ground on: skip the model call, which also saves a daily request
                reply = NO_ANSWER
                yield sse("token", text=reply)
            else:
                msgs = build_messages(skill, history, question, results, latest)

                if skill == "artifact":
                    yield sse("status", message="Building your artifact...")
                    full = "".join(stream_chat(msgs, max_tokens=6000))
                    reply, artifact = extract_artifact(full)
                    yield sse("token", text=reply)
                    if artifact:
                        artifact["version"] = n_art + 1
                        yield sse("artifact", artifact=artifact)
                else:
                    cap = 3500 if skill == "ship30for30" else None
                    for piece in stream_chat(msgs, max_tokens=cap):
                        reply += piece
                        yield sse("token", text=piece)

                    if skill == "ship30for30":
                        words = len(reply.split())
                        if words < ESSAY_MIN or words > ESSAY_MAX:
                            yield sse("status", message=f"The draft is {words} words. Revising toward {ESSAY_TARGET}...")
                            try:
                                revised = "".join(stream_chat(
                                    revision_messages(msgs, reply, words, ESSAY_TARGET), max_tokens=3500)).strip()
                                if revised:
                                    reply = revised
                                    words = len(reply.split())
                                    yield sse("replace", text=reply)
                            except LLMError:
                                pass  # keep the first draft
                        yield sse("meta", words=words)

                # Flag quoted passages that are not word for word in the excerpts
                if results:
                    checked = reply + "\n" + (artifact["content"] if artifact else "")
                    bad = unverified_quotes(checked, results)
                    if bad:
                        yield sse("check", unverified=bad[:5])
        except LLMError as e:
            yield sse("error", message=str(e))
        except psycopg.Error:
            log.exception("DB error during chat")
            yield sse("error", message="The database had a problem. Please try again.")
        except Exception:
            log.exception("Unexpected error during chat")
            yield sse("error", message="Something went wrong on the server. Please try again.")
        finally:
            # Runs on success, on error and when the user clicks Stop
            if reply:
                try:
                    message_id = save_assistant(session_id, reply, sources, skill)
                    if artifact:
                        save_artifact(session_id, message_id, artifact)
                except Exception:
                    log.exception("Could not save assistant message")
        yield sse("done")

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})