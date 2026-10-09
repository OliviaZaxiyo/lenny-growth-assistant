import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

type Artifact = { id: string; type: 'html' | 'markdown'; title: string; content: string; message_id?: string }
type Source = { n: number; guest: string; title: string; url: string | null }
type Msg = {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[] | null
  error?: string
  skill?: string
  reason?: string
  words?: number
  status?: string
  artifact?: Artifact
  unverified?: string[]
}
type ApiMsg = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[] | null
  skill_used?: string | null
}
type SessionRow = { id: string; title: string }
type Mode = 'auto' | 'qa' | 'essay' | 'artifact'

const MODES: { id: Mode; label: string }[] = [
  { id: 'auto', label: 'Auto' },
  { id: 'qa', label: 'Q&A' },
  { id: 'essay', label: 'Essay' },
  { id: 'artifact', label: 'Artifact' },
]
const SKILL_LABEL: Record<string, string> = {
  qa: 'Q&A',
  ship30for30: 'Ship 30 essay',
  artifact: 'Artifact',
}
const SUGGESTIONS = [
  'How should I price my product early on?',
  'Write an essay on pricing for early-stage startups',
  'Make a landing page with pricing lessons',
]

function getUserId(): string {
  let id = localStorage.getItem('lenny_user_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('lenny_user_id', id)
  }
  return id
}

function ArtifactPanel({ artifact, onClose }: { artifact: Artifact; onClose: () => void }) {
  const [tab, setTab] = useState<'preview' | 'code'>('preview')
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(artifact.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard not available */
    }
  }

  const tabClass = (t: string) =>
    `rounded-md px-3 py-1 text-xs font-medium ${tab === t ? 'bg-white shadow-sm' : 'text-slate-500 hover:text-slate-800'}`

  return (
    <section className="flex w-[48%] min-w-[360px] shrink-0 flex-col border-l border-slate-200 bg-white">
      <header className="flex items-center gap-3 border-b border-slate-200 px-4 py-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{artifact.title}</p>
          <p className="text-xs text-slate-500">{artifact.type === 'html' ? 'HTML page' : 'Markdown document'}</p>
        </div>
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
          <button onClick={() => setTab('preview')} className={tabClass('preview')}>Preview</button>
          <button onClick={() => setTab('code')} className={tabClass('code')}>Code</button>
        </div>
        <button onClick={copy} className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50">
          {copied ? 'Copied' : 'Copy'}
        </button>
        <button onClick={onClose} aria-label="Close viewer" className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100">
          ✕
        </button>
      </header>

      <div className="min-h-0 flex-1">
        {tab === 'code' ? (
          <pre className="h-full overflow-auto bg-slate-900 p-4 text-xs text-slate-100">{artifact.content}</pre>
        ) : artifact.type === 'html' ? (
          <iframe
            title={artifact.title}
            srcDoc={artifact.content}
            sandbox="allow-scripts"
            className="h-full w-full bg-white"
          />
        ) : (
          <div className="md h-full overflow-y-auto p-6">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </section>
  )
}

export default function App() {
  const [userId] = useState(getUserId)
  const [sessions, setSessions] = useState<SessionRow[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<Mode>('auto')
  const [busy, setBusy] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const [openArtifact, setOpenArtifact] = useState<Artifact | null>(null)
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
      const arts: Artifact[] = data.artifacts ?? []
      setActiveId(id)
      setMessages(
        (data.messages as ApiMsg[]).map(m => {
          const mine = arts.filter(a => a.message_id === m.id)
          return {
            id: m.id,
            role: m.role,
            content: m.content,
            sources: m.sources,
            skill: m.skill_used ?? undefined,
            artifact: mine.length ? mine[mine.length - 1] : undefined,
          }
        }),
      )
      setOpenArtifact(arts.length ? arts[arts.length - 1] : null)
    } catch {
      setBanner('Could not load that chat.')
    }
  }

  function newChat() {
    if (busy) return
    setActiveId(null)
    setMessages([])
    setOpenArtifact(null)
    setBanner(null)
  }

  function updateLast(fn: (m: Msg) => Msg) {
    setMessages(ms => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)))
  }

  function openEssay(m: Msg, i: number) {
    const title = m.content.match(/^#\s+(.+)$/m)?.[1] ?? 'Essay'
    setOpenArtifact({ id: `essay-${i}`, type: 'markdown', title, content: m.content })
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
        body: JSON.stringify({ content: text, mode }),
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
          if (ev.type === 'skill') updateLast(m => ({ ...m, skill: ev.skill, reason: ev.reason }))
          else if (ev.type === 'sources') updateLast(m => ({ ...m, sources: ev.sources }))
          else if (ev.type === 'token') updateLast(m => ({ ...m, content: m.content + ev.text }))
          else if (ev.type === 'status') updateLast(m => ({ ...m, status: ev.message }))
          else if (ev.type === 'replace') updateLast(m => ({ ...m, content: ev.text, status: undefined }))
          else if (ev.type === 'meta') updateLast(m => ({ ...m, words: ev.words }))
          else if (ev.type === 'check') updateLast(m => ({ ...m, unverified: ev.unverified }))
          else if (ev.type === 'artifact') {
            updateLast(m => ({ ...m, artifact: ev.artifact }))
            setOpenArtifact(ev.artifact)
          } else if (ev.type === 'error') updateLast(m => ({ ...m, error: ev.message }))
        }
      }
    } catch (e) {
      const err = e as Error
      if (err.name === 'AbortError') return
      setBanner(err instanceof TypeError ? 'Cannot reach the server. Is the backend running?' : err.message)
    } finally {
      updateLast(m => ({ ...m, status: undefined }))
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
              <div className="pt-20 text-center">
                <p className="text-slate-500">
                  Ask a product or growth question. Answers come only from Lenny's Podcast.
                </p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map(s => (
                    <button key={s} onClick={() => setInput(s)}
                            className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === 'user' ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl bg-indigo-600 px-4 py-2 text-white">{m.content}</div>
                </div>
              ) : (
                <div key={i} className="rounded-2xl bg-white px-4 py-3 shadow-sm">
                  {(m.skill || m.words) && (
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                      {m.skill && (
                        <span title={m.reason ?? ''} className="rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700">
                          {SKILL_LABEL[m.skill] ?? m.skill}
                        </span>
                      )}
                      {m.words ? <span className="text-slate-500">{m.words.toLocaleString()} words</span> : null}
                    </div>
                  )}

                  {m.content ? (
                    <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div>
                  ) : !m.error ? (
                    <span className="text-slate-400">{m.status ?? 'Thinking…'}</span>
                  ) : null}

                  {m.status && m.content && <p className="mt-2 text-xs text-indigo-600">{m.status}</p>}
                  {m.error && <p className="text-sm text-red-600">{m.error}</p>}

                  {m.unverified && m.unverified.length > 0 && (
                    <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      <p className="font-medium">Quotation marks removed: these passages were paraphrases, not word-for-word quotes.</p>
                      <ul className="mt-1 list-disc pl-4">
                        {m.unverified.map((q, k) => (
                          <li key={k}>{q.length > 140 ? q.slice(0, 140) + '…' : q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {m.artifact && (
                    <button onClick={() => setOpenArtifact(m.artifact!)}
                            className="mt-3 flex w-full items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-left text-sm hover:bg-slate-50">
                      <span className="truncate font-medium">{m.artifact.title}</span>
                      <span className="ml-3 shrink-0 text-xs text-slate-500">
                        {m.artifact.type === 'html' ? 'HTML' : 'Markdown'} · Open
                      </span>
                    </button>
                  )}

                  {m.skill === 'ship30for30' && m.content && !busy && (
                    <button onClick={() => openEssay(m, i)}
                            className="mt-3 rounded-lg border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50">
                      Open as document
                    </button>
                  )}

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
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex gap-1">
              {MODES.map(md => (
                <button
                  key={md.id}
                  onClick={() => setMode(md.id)}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${mode === md.id ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                >
                  {md.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
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
        </div>
      </main>

      {openArtifact && (
        <ArtifactPanel key={openArtifact.id} artifact={openArtifact} onClose={() => setOpenArtifact(null)} />
      )}
    </div>
  )
}