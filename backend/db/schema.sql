-- Enable pgvector extension
create extension if not exists vector;

-- Sessions
create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  interview_type text not null check (interview_type in ('behavioral', 'technical', 'general')),
  role text,
  difficulty integer default 3 check (difficulty between 1 and 5),
  status text default 'active' check (status in ('active', 'completed')),
  turn_count integer default 0,
  created_at timestamptz default now(),
  completed_at timestamptz
);

-- Row-level security
alter table sessions enable row level security;
create policy "Users can access own sessions"
  on sessions for all
  using (auth.uid() = user_id);

-- Messages (Q&A turns)
create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  role text not null check (role in ('interviewer', 'user', 'coach')),
  content text not null,
  competency text,
  score integer check (score between 1 and 5),
  turn_number integer,
  is_followup boolean default false,
  created_at timestamptz default now()
);

alter table messages enable row level security;
create policy "Users can access messages in own sessions"
  on messages for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- RAG embeddings (pgvector)
create table if not exists message_embeddings (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  message_id uuid references messages(id) on delete cascade,
  embedding vector(1536),
  content text,
  metadata jsonb
);

alter table message_embeddings enable row level security;
create policy "Users can access embeddings in own sessions"
  on message_embeddings for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- Resume documents attached to interview sessions
create table if not exists session_resumes (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  source_type text not null default 'text' check (source_type in ('text', 'upload')),
  filename text,
  content text not null,
  status text default 'processed' check (status in ('pending', 'processed', 'failed')),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(session_id)
);

alter table session_resumes enable row level security;
create policy "Users can access own session resumes"
  on session_resumes for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- Job descriptions attached to interview sessions
create table if not exists session_job_descriptions (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  source_type text not null default 'text' check (source_type in ('text', 'upload')),
  filename text,
  content text not null,
  status text default 'processed' check (status in ('pending', 'processed', 'failed')),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(session_id)
);

alter table session_job_descriptions enable row level security;
create policy "Users can access own session job descriptions"
  on session_job_descriptions for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- Shared document chunks for resume / JD RAG retrieval
create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  resume_id uuid references session_resumes(id) on delete cascade,
  job_description_id uuid references session_job_descriptions(id) on delete cascade,
  chunk_source text not null check (chunk_source in ('resume', 'jd')),
  chunk_index integer not null,
  content text not null,
  embedding vector(1536),
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  unique(resume_id, chunk_index),
  unique(job_description_id, chunk_index),
  check (
    (chunk_source = 'resume' and resume_id is not null and job_description_id is null)
    or
    (chunk_source = 'jd' and job_description_id is not null and resume_id is null)
  )
);

create index if not exists idx_document_chunks_session_source
  on document_chunks(session_id, chunk_source);

create index if not exists idx_document_chunks_resume
  on document_chunks(resume_id);

create index if not exists idx_document_chunks_job_description
  on document_chunks(job_description_id);

create index if not exists idx_document_chunks_embedding
  on document_chunks using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

alter table document_chunks enable row level security;
create policy "Users can access document chunks in own sessions"
  on document_chunks for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- Competency scores
create table if not exists competency_scores (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  competency text not null,
  score numeric default 0,
  attempts integer default 0,
  updated_at timestamptz default now(),
  unique(session_id, competency)
);

alter table competency_scores enable row level security;
create policy "Users can access competency scores in own sessions"
  on competency_scores for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- Session state snapshots for recoverable short-term memory
create table if not exists session_state_snapshots (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  turn_number integer not null default 0,
  snapshot_stage text not null default 'turn'
    check (snapshot_stage in ('created', 'started', 'turn', 'completed')),
  state jsonb not null,
  created_at timestamptz default now()
);

create index if not exists idx_session_state_snapshots_session_created
  on session_state_snapshots(session_id, created_at desc);

alter table session_state_snapshots enable row level security;
create policy "Users can access state snapshots in own sessions"
  on session_state_snapshots for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- Cross-session long-term user memories
create table if not exists user_memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  memory_type text not null
    check (memory_type in ('profile', 'project', 'strength', 'weakness', 'preference')),
  content text not null,
  embedding vector(1536),
  source_session_id uuid references sessions(id) on delete set null,
  confidence numeric not null default 0.8 check (confidence >= 0 and confidence <= 1),
  last_used_at timestamptz default now(),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, memory_type, content)
);

create index if not exists idx_user_memories_user_type
  on user_memories(user_id, memory_type);

create index if not exists idx_user_memories_last_used
  on user_memories(user_id, last_used_at desc);

create index if not exists idx_user_memories_embedding
  on user_memories using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

alter table user_memories enable row level security;
create policy "Users can access own long-term memories"
  on user_memories for all
  using (auth.uid() = user_id);

-- pgvector similarity search function
create or replace function match_session_embeddings(
  p_session_id uuid,
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    me.id,
    me.content,
    me.metadata,
    1 - (me.embedding <=> query_embedding) as similarity
  from message_embeddings me
  where
    me.session_id = p_session_id
    and 1 - (me.embedding <=> query_embedding) > match_threshold
  order by me.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function match_user_memories(
  p_user_id uuid,
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  p_memory_types text[] default null
)
returns table (
  id uuid,
  memory_type text,
  content text,
  confidence numeric,
  source_session_id uuid,
  last_used_at timestamptz,
  similarity float
)
language sql stable
as $$
  select
    um.id,
    um.memory_type,
    um.content,
    um.confidence,
    um.source_session_id,
    um.last_used_at,
    1 - (um.embedding <=> query_embedding) as similarity
  from user_memories um
  where
    um.user_id = p_user_id
    and um.embedding is not null
    and (p_memory_types is null or um.memory_type = any(p_memory_types))
    and 1 - (um.embedding <=> query_embedding) > match_threshold
  order by um.embedding <=> query_embedding, um.confidence desc, um.last_used_at desc
  limit match_count;
$$;

-- RAG evaluation results per turn (P0: LLM-as-Judge metrics)
create table if not exists rag_evaluations (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  message_id uuid references messages(id) on delete set null,
  turn_number integer not null,
  -- Core metrics (0.0 - 1.0)
  context_precision numeric,
  faithfulness numeric,
  answer_relevancy numeric,
  aggregate_score numeric,
  -- Weakness detection classification: TP / FP / FN / TN
  weakness_detection_outcome text,
  weakness_detection_correct boolean,
  -- Context info
  retrieved_chunks_count integer default 0,
  rag_matches_count integer default 0,
  -- Tool calls made by ReAct interviewer (P1)
  tool_calls jsonb default '[]'::jsonb,
  -- Full detail JSON for deep analysis
  detail jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_rag_evaluations_session
  on rag_evaluations(session_id, turn_number);

alter table rag_evaluations enable row level security;
create policy "Users can access rag evaluations in own sessions"
  on rag_evaluations for all
  using (
    session_id in (
      select id from sessions where user_id = auth.uid()
    )
  );

-- pgvector similarity search function for resume / JD chunks
create or replace function match_document_chunks(
  p_session_id uuid,
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  p_chunk_source text default null
)
returns table (
  id uuid,
  resume_id uuid,
  job_description_id uuid,
  chunk_source text,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.resume_id,
    dc.job_description_id,
    dc.chunk_source,
    dc.content,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  where
    dc.session_id = p_session_id
    and (p_chunk_source is null or dc.chunk_source = p_chunk_source)
    and 1 - (dc.embedding <=> query_embedding) > match_threshold
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;
