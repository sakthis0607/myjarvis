"""
Jarvis Web Server  (Groq + Supabase)
=====================================
Local:   py web/app.py
Deploy:  gunicorn wsgi:app
"""
import sys
import os
import threading

from flask import Flask, render_template, request, jsonify
import config
from core.llm    import chat as llm_chat, check_status as llm_status
from core.agent  import JarvisAgent
from core.skills import match_skill
from core.license import get_current_tier, get_features
from core.computer import TOOLS
import core.db as db

app = Flask(__name__)

# ── Session store — RAM fallback when Supabase not configured ─────────────────
_ram_sessions  = {}
_sessions_lock = threading.Lock()

def _get_history(sid: str) -> list:
    """Load from Supabase if available, else RAM."""
    if db.is_available():
        return db.load_history(sid)
    with _sessions_lock:
        return list(_ram_sessions.setdefault(sid, []))

def _add(sid: str, role: str, content: str):
    """Save to Supabase if available, always keep in RAM too."""
    if db.is_available():
        db.save_message(sid, role, content)
    with _sessions_lock:
        h = _ram_sessions.setdefault(sid, [])
        h.append({"role": role, "content": content})
        if len(h) > 40:
            _ram_sessions[sid] = h[-40:]

def _clear(sid: str):
    if db.is_available():
        db.clear_history(sid)
    with _sessions_lock:
        _ram_sessions[sid] = []


# ── Agent step collector ──────────────────────────────────────────────────────

class StepCollector:
    def __init__(self):
        self.steps = []
        self.final = ""

    def on_thought(self, text):
        import re, json as _j
        m = re.search(r'\{[^{}]*"tool"[^{}]*\}', text)
        if m:
            try:
                obj = _j.loads(m.group())
                self.steps.append({"type": "thought",
                    "text": f"Calling: {obj.get('tool')} {obj.get('args', {})}"})
                return
            except Exception:
                pass
        self.steps.append({"type": "thought", "text": text[:200]})

    def on_action(self, name, args):
        self.steps.append({"type": "action", "text": f"{name}({args})"})

    def on_result(self, result):
        d = result[:500] + "\n...(truncated)" if len(result) > 500 else result
        self.steps.append({"type": "result", "text": d})

    def on_final(self, text):
        self.final = text
        self.steps.append({"type": "final", "text": text})


_AGENT_KW = [
    "open", "launch", "create", "delete", "move", "copy", "find",
    "run", "execute", "list files", "show me", "read file", "write file",
    "search files", "screenshot", "battery", "cpu", "ram", "disk",
    "process", "kill", "system info", "clipboard", "what files", "folder",
]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data       = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()
    sid        = data.get("session_id", "default")

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    cfg     = config.load_config()
    tier    = get_current_tier()
    history = _get_history(sid)

    _add(sid, "user", user_input)

    # 1. Skill match
    skill = match_skill(user_input, tier)
    if skill:
        out = []
        skill["action"](user_input, lambda t: out.append(t))
        reply = out[0] if out else skill["description"]
        _add(sid, "assistant", reply)
        db.log_usage(sid, "skill")
        return jsonify({"reply": reply, "steps": [], "type": "skill"})

    # 2. Agent mode
    if any(kw in user_input.lower() for kw in _AGENT_KW):
        col   = StepCollector()
        agent = JarvisAgent(
            on_thought=col.on_thought,
            on_action =col.on_action,
            on_result =col.on_result,
            on_final  =col.on_final,
        )
        agent.run(user_input, history=history[:-1] if history else [])
        reply = col.final or "Done."
        _add(sid, "assistant", reply)
        db.log_usage(sid, "agent")
        return jsonify({"reply": reply, "steps": col.steps, "type": "agent"})

    # 3. Plain LLM chat
    features = get_features()
    max_hist = features.get("max_history", 10)
    messages = [{"role": "system", "content": cfg.get("system_prompt", "")}]
    messages += history[-(max_hist * 2):]

    try:
        reply = llm_chat(messages)
    except Exception as e:
        reply = f"Error: {e}"

    _add(sid, "assistant", reply)
    db.log_usage(sid, "chat", len(reply) // 4)
    return jsonify({"reply": reply, "steps": [], "type": "chat"})


@app.route("/api/clear", methods=["POST"])
def clear():
    data = request.get_json(silent=True) or {}
    _clear(data.get("session_id", "default"))
    return jsonify({"ok": True})


@app.route("/api/status")
def status():
    cfg  = config.load_config()
    tier = get_current_tier()
    st   = llm_status()
    return jsonify({
        "ok":        st["ok"],
        "provider":  st["provider"],
        "model":     st["model"],
        "error":     st.get("error", ""),
        "tier":      tier,
        "tools":     len(TOOLS),
        "name":      cfg.get("assistant_name", "Jarvis"),
        "db":        db.is_available(),
    })


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        cfg  = config.load_config()
        safe = {k: v for k, v in cfg.items() if k != "license_key"}
        if safe.get("groq_api_key"):
            safe["groq_api_key"] = "***set***"
        return jsonify(safe)

    data = request.get_json(silent=True) or {}
    cfg  = config.load_config()
    for key in ["assistant_name", "llm_provider", "groq_model",
                "ollama_model", "groq_api_key", "system_prompt", "max_history"]:
        if key in data and data[key] != "***set***":
            cfg[key] = data[key]
    config.save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/history/<session_id>")
def get_history_api(session_id):
    """Get full chat history for a session."""
    history = _get_history(session_id)
    return jsonify({"session_id": session_id, "messages": history})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("PORT", 5000)))
    args = parser.parse_args()
    print(f"\n  Jarvis running at http://localhost:{args.port}")
    print(f"  Database: {'Supabase' if db.is_available() else 'RAM (no Supabase configured)'}\n")
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
