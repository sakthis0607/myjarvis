"""
Jarvis AI Assistant - Skills / Command Registry
-------------------------------------------------
Skills are keyword-triggered actions that run before the LLM fallback.
Each skill is a dict: { "keywords": [...], "action": callable, "description": str }
"""
import webbrowser
import subprocess
import os
import datetime


def _open_url(url: str, label: str):
    def action(user_input: str, speak_fn) -> bool:
        speak_fn(f"Opening {label}.")
        webbrowser.open(url)
        return True
    return action


def _search_google(user_input: str, speak_fn) -> bool:
    query = user_input.replace("search", "").replace("google", "").strip()
    if query:
        speak_fn(f"Searching Google for {query}.")
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
    return True


def _search_youtube(user_input: str, speak_fn) -> bool:
    query = (user_input.replace("search youtube", "")
                       .replace("youtube search", "")
                       .replace("search on youtube", "")
                       .strip())
    if query:
        speak_fn(f"Searching YouTube for {query}.")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
    else:
        speak_fn("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")
    return True


def _tell_time(user_input: str, speak_fn) -> bool:
    now = datetime.datetime.now()
    speak_fn(f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}.")
    return True


def _open_vscode(user_input: str, speak_fn) -> bool:
    speak_fn("Opening VS Code.")
    try:
        subprocess.Popen(["code", "."], shell=True)
    except Exception:
        speak_fn("Could not open VS Code. Make sure it's installed and in your PATH.")
    return True


def _open_terminal(user_input: str, speak_fn) -> bool:
    speak_fn("Opening terminal.")
    try:
        subprocess.Popen("start cmd", shell=True)
    except Exception:
        speak_fn("Could not open terminal.")
    return True


def _open_calculator(user_input: str, speak_fn) -> bool:
    speak_fn("Opening calculator.")
    subprocess.Popen("calc", shell=True)
    return True


def _open_notepad(user_input: str, speak_fn) -> bool:
    speak_fn("Opening Notepad.")
    subprocess.Popen("notepad", shell=True)
    return True


def _open_any_app(user_input: str, speak_fn) -> bool:
    """Generic app opener — extracts app name from 'open X' or 'launch X'."""
    import re
    from core.computer import open_application
    match = re.search(r'(?:open|launch|start)\s+(.+)', user_input.lower())
    if match:
        app_name = match.group(1).strip()
        speak_fn(f"Opening {app_name}.")
        result = open_application(app_name)
        if not result["ok"]:
            speak_fn(result["error"])
    return True


# ── Skill Registry ──────────────────────────────────────────────────────────

SKILLS = [
    {
        "keywords": ["open youtube", "launch youtube"],
        "action": _open_url("https://www.youtube.com", "YouTube"),
        "description": "Open YouTube in browser",
        "tier": "free",
    },
    {
        "keywords": ["open google", "launch google"],
        "action": _open_url("https://www.google.com", "Google"),
        "description": "Open Google in browser",
        "tier": "free",
    },
    {
        "keywords": ["open spotify", "play music", "launch spotify"],
        "action": _open_url("https://open.spotify.com", "Spotify"),
        "description": "Open Spotify",
        "tier": "free",
    },
    {
        "keywords": ["open github", "launch github"],
        "action": _open_url("https://github.com", "GitHub"),
        "description": "Open GitHub",
        "tier": "free",
    },
    {
        "keywords": ["open chatgpt", "open chat gpt"],
        "action": _open_url("https://chat.openai.com", "ChatGPT"),
        "description": "Open ChatGPT",
        "tier": "free",
    },
    {
        "keywords": ["search youtube", "youtube search", "search on youtube"],
        "action": _search_youtube,
        "description": "Search YouTube",
        "tier": "free",
    },
    {
        "keywords": ["search google", "google search", "search for"],
        "action": _search_google,
        "description": "Search Google",
        "tier": "free",
    },
    {
        "keywords": ["what time is it", "what's the time", "current time", "tell me the time"],
        "action": _tell_time,
        "description": "Tell current time and date",
        "tier": "free",
    },
    {
        "keywords": ["open vs code", "open vscode", "launch vs code", "open code editor"],
        "action": _open_vscode,
        "description": "Open VS Code",
        "tier": "pro",
    },
    {
        "keywords": ["open terminal", "open command prompt", "open cmd"],
        "action": _open_terminal,
        "description": "Open terminal / command prompt",
        "tier": "pro",
    },
    {
        "keywords": ["open calculator", "launch calculator"],
        "action": _open_calculator,
        "description": "Open calculator",
        "tier": "free",
    },
    {
        "keywords": ["open notepad", "launch notepad"],
        "action": _open_notepad,
        "description": "Open Notepad",
        "tier": "free",
    },
    # ── Generic app opener — must be LAST so specific skills match first ──
    {
        "keywords": ["open ", "launch ", "start "],
        "action": _open_any_app,
        "description": "Open any installed application by name",
        "tier": "free",
    },
]


def match_skill(user_input: str, current_tier: str = "free"):
    """
    Find the first matching skill for the given input.
    Returns the skill dict or None.
    """
    text = user_input.lower().strip()
    tier_order = ["free", "pro", "enterprise"]
    user_tier_level = tier_order.index(current_tier) if current_tier in tier_order else 0

    for skill in SKILLS:
        skill_tier_level = tier_order.index(skill.get("tier", "free"))
        if skill_tier_level > user_tier_level:
            continue  # Skill requires higher tier
        for kw in skill["keywords"]:
            if kw in text:
                return skill
    return None


def list_skills(current_tier: str = "free") -> list:
    """Return all skills available for the given tier."""
    tier_order = ["free", "pro", "enterprise"]
    user_tier_level = tier_order.index(current_tier) if current_tier in tier_order else 0
    return [
        s for s in SKILLS
        if tier_order.index(s.get("tier", "free")) <= user_tier_level
    ]
