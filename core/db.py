"""
Jarvis - Supabase Database Layer
==================================
Stores conversation history, settings, and usage logs.

Tables needed (run the SQL in Supabase dashboard):
  See setup_sql() below or copy from README.
"""
import os
import json
import datetime

# Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # use anon/public key

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _client
    except Exception:
        return None


def is_available() -> bool:
    """Check if Supabase is configured and reachable."""
    return _get_client() is not None


# ── Conversation History ──────────────────────────────────────────────────────

def load_history(session_id: str) -> list:
    """Load conversation history for a session from Supabase."""
    db = _get_client()
    if db is None:
        return []
    try:
        res = (db.table("conversations")
               .select("role, content")
               .eq("session_id", session_id)
               .order("created_at")
               .limit(40)
               .execute())
        return [{"role": r["role"], "content": r["content"]} for r in (res.data or [])]
    except Exception:
        return []


def save_message(session_id: str, role: str, content: str):
    """Save a single message to Supabase."""
    db = _get_client()
    if db is None:
        return
    try:
        db.table("conversations").insert({
            "session_id": session_id,
            "role":       role,
            "content":    content,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


def clear_history(session_id: str):
    """Delete all messages for a session."""
    db = _get_client()
    if db is None:
        return
    try:
        db.table("conversations").delete().eq("session_id", session_id).execute()
    except Exception:
        pass


def get_all_sessions() -> list:
    """Get list of all unique session IDs."""
    db = _get_client()
    if db is None:
        return []
    try:
        res = (db.table("conversations")
               .select("session_id")
               .execute())
        seen = set()
        sessions = []
        for r in (res.data or []):
            sid = r["session_id"]
            if sid not in seen:
                seen.add(sid)
                sessions.append(sid)
        return sessions
    except Exception:
        return []


# ── Usage Logs ────────────────────────────────────────────────────────────────

def log_usage(session_id: str, msg_type: str, tokens_approx: int = 0):
    """Log API usage for analytics."""
    db = _get_client()
    if db is None:
        return
    try:
        db.table("usage_logs").insert({
            "session_id":    session_id,
            "type":          msg_type,   # "chat" | "agent" | "skill"
            "tokens_approx": tokens_approx,
            "created_at":    datetime.datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


# ── SQL to run once in Supabase dashboard ─────────────────────────────────────

SETUP_SQL = """
-- Run this once in your Supabase SQL editor

-- Conversation history table
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast session lookups
CREATE INDEX IF NOT EXISTS idx_conversations_session
    ON conversations(session_id, created_at);

-- Usage logs table
CREATE TABLE IF NOT EXISTS usage_logs (
    id             BIGSERIAL PRIMARY KEY,
    session_id     TEXT NOT NULL,
    type           TEXT NOT NULL,
    tokens_approx  INTEGER DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-delete old messages (keep last 30 days)
CREATE OR REPLACE FUNCTION delete_old_messages()
RETURNS void AS $$
BEGIN
    DELETE FROM conversations
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
"""


def print_setup_sql():
    print(SETUP_SQL)
