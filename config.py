"""
Jarvis AI Assistant - Configuration & Settings
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "jarvis_config.json")

DEFAULT_CONFIG = {
    "assistant_name": "Jarvis",
    "voice_index": 0,
    "speech_rate": 175,
    "llm_provider": "groq",                       # "groq" or "ollama"
    "groq_api_key": "",                            # get free key: console.groq.com
    "groq_model":   "llama-3.3-70b-versatile",    # fast & free on Groq
    "ollama_model": "llama3.2",                   # used only when provider=ollama
    "system_prompt": (
        "You are Jarvis, a highly intelligent AI assistant. "
        "Be concise, practical, and conversational. "
        "When helping with code, provide clean examples. "
        "Keep responses under 3 sentences unless more detail is needed."
    ),
    "max_history": 10,
    "theme": "dark",
    "license_key": "",
    "tier": "free",
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            return {**DEFAULT_CONFIG, **saved}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get(key: str):
    return load_config().get(key, DEFAULT_CONFIG.get(key))

def set_value(key: str, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
