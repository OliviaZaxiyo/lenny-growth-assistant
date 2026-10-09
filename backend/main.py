"""FastAPI app: sessions, history and the streaming chat endpoint."""
import json
import logging
import os
from uuid import UUID

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from db import connect
from llm import LLMError, current_config, stream_chat
from prompts import build_messages
from retrieval import search

load_dotenv()
log = logging.getLogger("app")

app = FastAPI(title="Lenny Growth Assistant")

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.getenv("FRONTEND_ORIGIN"):
    origins.append(os.getenv("FRONTEND_ORIGIN"))
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

NO_ANSWER = ("I couldn't find anything in the podcast transcripts that matches that question. "
             "Try rephrasing it or using more specific terms.")


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
    return {**s, "messages": msgs}


def sse(kind: str, **data) -> str:
    return f"data: {json.dumps({'type': kind, **data})}\n\n"


def save_assistant(session_id, text, sources):
    with connect() as conn:
        conn.execute(
            "insert into messages (session_id, role, content, skill_used, sources) "
            "values (%s, 'assistant', %s, 'qa', %s)",
            (session_id, text, Jsonb(sources)),
        )
        conn.execute("update sessions set updated_at = now() where id = %s", (session_id,))


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
        conn.execute(
            "insert into messages (session_id, role, content) values (%s, 'user', %s)",
            (session_id, question),
        )
        if s["title"] == "New chat":
            conn.execute("update sessions set title = %s where id = %s", (question[:60], session_id))

    def generate():
        reply, sources = "", []
        try:
            results, _used = search(question)
            sources = [{"n": i, "guest": r["guest"], "title": r["title"], "url": r["url"]}
                       for i, r in enumerate(results, start=1)]
            yield sse("sources", sources=sources)

            if not results:
                # No excerpts: skip the model call, which also saves a daily request
                reply = NO_ANSWER
                yield sse("token", text=reply)
            else:
                for piece in stream_chat(build_messages(history, question, results)):
                    reply += piece
                    yield sse("token", text=piece)
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
                    save_assistant(session_id, reply, sources)
                except Exception:
                    log.exception("Could not save assistant message")
        yield sse("done")

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})