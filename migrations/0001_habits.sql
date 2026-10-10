-- Habits cell: habits and routines with their daily logs, plus the outbox for
-- graph events and create-key reservations. Every row belongs to a workspace
-- and is visible only while the transaction is bound to it (app.workspace_id).

CREATE SCHEMA habits;

CREATE FUNCTION habits.current_workspace() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT nullif(current_setting('app.workspace_id', true), '')::uuid
$$;

CREATE TABLE habits.habits (
    workspace_id            uuid NOT NULL,
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    legacy_id               bigint,
    name                    text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
    slug                    text NOT NULL CHECK (slug ~ '^[a-z0-9][a-z0-9-]{0,99}$'),
    description             text,
    category                text NOT NULL DEFAULT 'productivity' CHECK (category IN (
        'health', 'learning', 'business', 'creative', 'mindfulness', 'productivity', 'social', 'financial')),
    frequency               text NOT NULL DEFAULT 'daily' CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    target_count            integer NOT NULL DEFAULT 1 CHECK (target_count >= 1),
    target_duration_minutes integer CHECK (target_duration_minutes IS NULL OR target_duration_minutes >= 0),
    status                  text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    priority                integer NOT NULL DEFAULT 3 CHECK (priority BETWEEN 0 AND 10),
    current_streak          integer NOT NULL DEFAULT 0 CHECK (current_streak >= 0),
    best_streak             integer NOT NULL DEFAULT 0 CHECK (best_streak >= 0),
    last_completed_at       date,
    schedule_days           jsonb CHECK (schedule_days IS NULL OR jsonb_typeof(schedule_days) = 'array'),
    preferred_time          text,
    notes                   text,
    version                 bigint NOT NULL DEFAULT 1,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, id),
    UNIQUE (workspace_id, slug)
);
CREATE UNIQUE INDEX habits_legacy ON habits.habits (workspace_id, legacy_id) WHERE legacy_id IS NOT NULL;
CREATE INDEX habits_status ON habits.habits (workspace_id, status);
CREATE INDEX habits_category ON habits.habits (workspace_id, category);

CREATE TABLE habits.habit_logs (
    workspace_id     uuid NOT NULL,
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    habit_id         bigint NOT NULL,
    log_date         date NOT NULL,
    completed        boolean NOT NULL DEFAULT true,
    count            integer NOT NULL DEFAULT 1 CHECK (count >= 0),
    duration_minutes integer CHECK (duration_minutes IS NULL OR duration_minutes >= 0),
    notes            text,
    version          bigint NOT NULL DEFAULT 1,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, habit_id, log_date),
    FOREIGN KEY (workspace_id, habit_id) REFERENCES habits.habits (workspace_id, id) ON DELETE CASCADE
);
CREATE INDEX habit_logs_date ON habits.habit_logs (workspace_id, log_date);

CREATE TABLE habits.routines (
    workspace_id           uuid NOT NULL,
    id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    legacy_id              bigint,
    name                   text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
    slug                   text NOT NULL CHECK (slug ~ '^[a-z0-9][a-z0-9-]{0,99}$'),
    description            text,
    routine_type           text NOT NULL DEFAULT 'daily_morning' CHECK (routine_type IN (
        'daily_morning', 'daily_evening', 'weekly_review', 'monthly_review', 'custom')),
    steps                  jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(steps) = 'array'),
    status                 text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
    total_duration_minutes integer CHECK (total_duration_minutes IS NULL OR total_duration_minutes >= 0),
    version                bigint NOT NULL DEFAULT 1,
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, id),
    UNIQUE (workspace_id, slug)
);
CREATE UNIQUE INDEX routines_legacy ON habits.routines (workspace_id, legacy_id) WHERE legacy_id IS NOT NULL;
CREATE INDEX routines_type ON habits.routines (workspace_id, routine_type);

CREATE TABLE habits.routine_logs (
    workspace_id     uuid NOT NULL,
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    routine_id       bigint NOT NULL,
    log_date         date NOT NULL,
    completed_steps  jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(completed_steps) = 'array'),
    skipped_steps    jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(skipped_steps) = 'array'),
    duration_minutes integer CHECK (duration_minutes IS NULL OR duration_minutes >= 0),
    mood_before      integer CHECK (mood_before IS NULL OR mood_before BETWEEN 1 AND 5),
    mood_after       integer CHECK (mood_after IS NULL OR mood_after BETWEEN 1 AND 5),
    notes            text,
    version          bigint NOT NULL DEFAULT 1,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, routine_id, log_date),
    FOREIGN KEY (workspace_id, routine_id) REFERENCES habits.routines (workspace_id, id) ON DELETE CASCADE
);
CREATE INDEX routine_logs_date ON habits.routine_logs (workspace_id, log_date);

-- Idempotent creates: a key reserves the record id before the platform execution starts.
CREATE TABLE habits.create_keys (
    workspace_id uuid NOT NULL,
    actor        uuid NOT NULL,
    kind         text NOT NULL CHECK (kind IN ('habit', 'routine')),
    key          text NOT NULL CHECK (length(key) BETWEEN 8 AND 200),
    record_id    bigint NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, actor, kind, key)
);

-- Graph events, written in the same transaction as the change (at-least-once delivery).
CREATE TABLE habits.outbox (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    uuid NOT NULL,
    type            text NOT NULL,
    subject         text NOT NULL,
    execution_id    uuid,
    classification  text NOT NULL DEFAULT 'confidential',
    payload         jsonb NOT NULL,
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    published_at    timestamptz,
    attempts        integer NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    last_error      text,
    correlation_id  text
);
CREATE INDEX outbox_pending ON habits.outbox (next_attempt_at) WHERE published_at IS NULL;

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['habits', 'habit_logs', 'routines', 'routine_logs', 'create_keys', 'outbox'] LOOP
        EXECUTE format('ALTER TABLE habits.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE habits.%I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('CREATE POLICY workspace_isolation ON habits.%I'
                       ' USING (workspace_id = habits.current_workspace())'
                       ' WITH CHECK (workspace_id = habits.current_workspace())', t);
    END LOOP;
END
$$;

GRANT USAGE ON SCHEMA habits TO habits_api;
GRANT EXECUTE ON FUNCTION habits.current_workspace() TO habits_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON habits.habits, habits.habit_logs, habits.routines, habits.routine_logs
    TO habits_api;
GRANT SELECT, INSERT ON habits.create_keys TO habits_api;
GRANT USAGE ON SEQUENCE habits.habits_id_seq, habits.routines_id_seq TO habits_api;
GRANT SELECT, INSERT ON habits.outbox TO habits_api;
GRANT UPDATE (execution_id, published_at, attempts, next_attempt_at, last_error) ON habits.outbox TO habits_api;

-- The publisher sweeps the outbox of one workspace per token; it reads past RLS for the outbox only.
CREATE POLICY publisher_sweep ON habits.outbox TO habits_publisher USING (true) WITH CHECK (true);
GRANT USAGE ON SCHEMA habits TO habits_publisher;
GRANT SELECT ON habits.outbox TO habits_publisher;
GRANT UPDATE (published_at, attempts, next_attempt_at, last_error) ON habits.outbox TO habits_publisher;
