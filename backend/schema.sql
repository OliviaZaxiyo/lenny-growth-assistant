create extension if not exists vector;

-- Who is chatting (anonymous browser id for now)
create table if not exists users (
    id          uuid primary key default gen_random_uuid(),
    created_at  timestamptz not null default now(),
    metadata    jsonb not null default '{}'
);

-- One row per "New Chat"
create table if not exists sessions (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    title       text not null default 'New chat',
    model       text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Every message in every session
create table if not exists messages (
    id          uuid primary key default gen_random_uuid(),
    session_id  uuid not null references sessions(id) on delete cascade,
    role        text not null check (role in ('user', 'assistant', 'system')),
    content     text not null,
    skill_used  text,
    sources     jsonb,
    created_at  timestamptz not null default now()
);

-- HTML / Markdown artifacts the AI generates
create table if not exists artifacts (
    id          uuid primary key default gen_random_uuid(),
    session_id  uuid not null references sessions(id) on delete cascade,
    message_id  uuid references messages(id) on delete set null,
    type        text not null check (type in ('html', 'markdown')),
    title       text not null,
    content     text not null,
    version     int not null default 1,
    created_at  timestamptz not null default now()
);

-- Knowledge base: one row per podcast episode
create table if not exists episodes (
    id            serial primary key,
    slug          text unique not null,
    guest         text,
    title         text,
    youtube_url   text,
    publish_date  date
);

-- Knowledge base: searchable pieces of each transcript
create table if not exists chunks (
    id             bigserial primary key,
    episode_id     int not null references episodes(id) on delete cascade,
    chunk_index    int not null,
    start_seconds  int,
    speaker        text,
    content        text not null,
    embedding      vector(384),
    tsv            tsvector generated always as (to_tsvector('english', content)) stored
);

create index if not exists idx_sessions_user   on sessions(user_id, updated_at desc);
create index if not exists idx_messages_session on messages(session_id, created_at);
create index if not exists idx_artifacts_session on artifacts(session_id);
create index if not exists idx_chunks_episode   on chunks(episode_id);
create index if not exists idx_chunks_tsv       on chunks using gin(tsv);