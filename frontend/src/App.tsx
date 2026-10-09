import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

type Source = { n: number; guest: string; title: string; url: string | null }
type Msg = { role: 'user' | 'assistant'; content: string; sources?: Source[] | null; error?: string }
type SessionRow = { id: string; title: string }

function getUserId(): string {
  let id = localStorage.getItem('lenny_user_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('lenny_user_id', id)
  }
  return id
}

export default function App() {
  const [userId] = useState(getUserId)
  const [sessions, setSessions] = useState<SessionRow[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  async function loadSessions() {
    try {
      const r = await fetch(`${API}/sessions?user_id=${userId}`)
      if (!r.ok) throw new Error()
      setSessions(await r.json())
    } catch {
      setBanner('Cannot reach the server. Is the backend running?')
    }
  }

  useEffect(() => { loadSessions() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function openSession(id: string) {
    if (busy) return
    setBanner(null)
    try {
      const r = await fetch(`${API}/sessions/${id}`)
      if (!r.ok) throw new Error()
      const data = await r.json()
      setActiveId(id)
      setMessages(data.messages.map((m: Msg) => ({ role: m.role, content: m.content, sources: m.sources })))
    } catch {
      setBanner('Could not load that chat.')
    }
  }

  function newChat() {
    if (busy) return
    setActiveId(null)
    setMessages([])
    setBanner(null)
  }

  function updateLast(fn: (m: Msg) => Msg) {
    setMessages(ms => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)))
  }

  async function send() {
    const text = input.trim()
    if (!text || busy) return
    setBanner(null)
    setInput('')
    setBusy(true)
    try {
      let sid = activeId
      if (!sid) {
        const r = await fetch(`${API}/sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId }),
        })
        if (!r.ok) throw new Error('Could not create a chat session.')
        sid = (await r.json()).id as string
        setActiveId(sid)
      }
      setMessages(m => [...m, { role: 'user', content: text }, { role: 'assistant', content: '', sources: null }])

      const ctrl = new AbortController()
      abortRef.current = ctrl
      const res = await fetch(`${API}/sessions/${sid}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
        signal: ctrl.signal,
      })
      if (!res.ok || !res.body) {
        const d = await res.json().catch(() => null)
        throw new Error(d?.detail ?? 'The server returned an error.')
      }

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''
        for (const p of parts) {
          if (!p.startsWith('data: ')) continue
          const ev = JSON.parse(p.slice(6))
          if (ev.type === 'sources') updateLast(m => ({ ...m, sources: ev.sources }))
          else if (ev.type === 'token') updateLast(m => ({ ...m, content: m.content + ev.text }))
          else if (ev.type === 'error') updateLast(m => ({ ...m, error: ev.message }))
        }
      }
    } catch (e) {
      const err = e as Error
      if (err.name === 'AbortError') return
      setBanner(err instanceof TypeError ? 'Cannot reach the server. Is the backend running?' : err.message)
    } finally {
      setBusy(false)
      abortRef.current = null
      loadSessions()
    }
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-64 shrink-0 flex-col bg-slate-900 p-3 text-slate-100">
        <button onClick={newChat} className="mb-3 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium hover:bg-indigo-500">
          + New chat
        </button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {sessions.map(s => (
            <button
              key={s.id}
              onClick={() => openSession(s.id)}
              className={`block w-full truncate rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-800 ${s.id === activeId ? 'bg-slate-800' : ''}`}
            >
              {s.title}
            </button>
          ))}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white px-6 py-3 text-sm font-semibold">
          Lenny Growth Assistant
        </header>

        {banner && <div className="bg-red-50 px-6 py-2 text-sm text-red-700">{banner}</div>}

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-3xl space-y-5">
            {messages.length === 0 && (
              <p className="pt-24 text-center text-slate-500">
                Ask a product or growth question. Answers come only from Lenny's Podcast.
              </p>
            )}
            {messages.map((m, i) =>
              m.role === 'user' ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl bg-indigo-600 px-4 py-2 text-white">{m.content}</div>
                </div>
              ) : (
                <div key={i} className="rounded-2xl bg-white px-4 py-3 shadow-sm">
                  {m.content ? (
                    <div className="md"><ReactMarkdown>{m.content}</ReactMarkdown></div>
                  ) : !m.error ? (
                    <span className="text-slate-400">Thinking…</span>
                  ) : null}
                  {m.error && <p className="text-sm text-red-600">{m.error}</p>}
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3 text-xs">
                      {m.sources.map(s =>
                        s.url ? (
                          <a key={s.n} href={s.url} target="_blank" rel="noreferrer"
                             className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 hover:bg-slate-200">
                            [{s.n}] {s.guest}
                          </a>
                        ) : (
                          <span key={s.n} className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                            [{s.n}] {s.guest}
                          </span>
                        ),
                      )}
                    </div>
                  )}
                </div>
              ),
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-slate-200 bg-white p-4">
          <div className="mx-auto flex max-w-3xl gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') send() }}
              placeholder="Ask about pricing, growth, hiring…"
              className="flex-1 rounded-xl border border-slate-300 px-4 py-2 outline-none focus:border-indigo-500"
            />
            {busy ? (
              <button onClick={() => abortRef.current?.abort()} className="rounded-xl bg-slate-700 px-4 py-2 text-white">Stop</button>
            ) : (
              <button onClick={send} className="rounded-xl bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-500">Send</button>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}