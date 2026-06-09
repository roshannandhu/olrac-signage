-- Olrac Signage — Supabase schema migration
-- Run this once in Supabase → SQL Editor → New query

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── PROFILES ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── CONTENT ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('video', 'image')),
    orientation TEXT NOT NULL CHECK (orientation IN ('landscape', 'portrait')),
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    file_size BIGINT NOT NULL DEFAULT 0,
    tags TEXT[] NOT NULL DEFAULT '{}',
    start_date TIMESTAMPTZ,
    expiry_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── SCREENS ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS screens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    name TEXT NOT NULL DEFAULT 'Unpaired screen',
    description TEXT,
    pairing_code TEXT,
    pairing_code_expires_at TIMESTAMPTZ,
    orientation TEXT NOT NULL DEFAULT 'D0' CHECK (orientation IN ('D0', 'D90', 'D180', 'D270')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'online', 'offline')),
    last_seen_at TIMESTAMPTZ,
    screen_token TEXT NOT NULL UNIQUE,
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── SCREEN GROUPS ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS screen_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS group_screens (
    group_id UUID NOT NULL REFERENCES screen_groups(id) ON DELETE CASCADE,
    screen_id UUID NOT NULL REFERENCES screens(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, screen_id)
);

-- ── PLAYLISTS ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS playlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID UNIQUE REFERENCES screens(id) ON DELETE CASCADE,
    group_id UUID UNIQUE REFERENCES screen_groups(id) ON DELETE CASCADE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_playlist_owner CHECK (
        (screen_id IS NOT NULL AND group_id IS NULL)
        OR (screen_id IS NULL AND group_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS playlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playlist_id UUID NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    duration_override INTEGER
);

-- ── WEBSITES ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS websites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── PLAYBACK LOGS ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS playback_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID NOT NULL REFERENCES screens(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    played_at TIMESTAMPTZ NOT NULL,
    duration_played INTEGER NOT NULL
);

-- ── INDEXES ────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_content_owner ON content(owner_id);
CREATE INDEX IF NOT EXISTS idx_screens_owner ON screens(owner_id);
CREATE INDEX IF NOT EXISTS idx_screens_pairing_code ON screens(pairing_code);
CREATE INDEX IF NOT EXISTS idx_screens_screen_token ON screens(screen_token);
CREATE INDEX IF NOT EXISTS idx_playlist_items_playlist ON playlist_items(playlist_id);
CREATE INDEX IF NOT EXISTS idx_group_screens_group ON group_screens(group_id);
CREATE INDEX IF NOT EXISTS idx_group_screens_screen ON group_screens(screen_id);
CREATE INDEX IF NOT EXISTS idx_playback_logs_screen ON playback_logs(screen_id);
CREATE INDEX IF NOT EXISTS idx_playback_logs_played_at ON playback_logs(played_at);
