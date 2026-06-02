"""
Jarvis - LLM Abstraction Layer
================================
Supports Groq (cloud, free) and Ollama (local).
Provider is selected via config: llm_provider = "groq" | "ollama"

Groq free tier: https://console.groq.com
  - llama-3.3-70b-versatile  (best quality, free)
  - llama-3.1-8b-instant     (fastest, free)
  - mixtral-8x7b-32768       (long context, free)
"""
import os
import config


def _get_groq_client():
    from groq import Groq
    cfg = config.load_config()
    # Priority: env var > config file
    api_key = os.environ.get("GROQ_API_KEY") or cfg.get("groq_api_key", "")
    if not api_key:
        raise ValueError(
            "Groq API key not set. "
            "Get a free key at https://console.groq.com "
            "then set GROQ_API_KEY environment variable or add it in Settings."
        )
    return Groq(api_key=api_key)


def chat(messages: list, stream: bool = False) -> str:
    """
    Send messages to the configured LLM and return the reply text.
    Always uses Groq on the server (set via GROQ_API_KEY env var).
    """
    # Always prefer env var — this is what Render sets
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        from groq import Groq
        model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    # Fall back to config file (local development)
    cfg      = config.load_config()
    provider = cfg.get("llm_provider", "groq")

    if provider == "groq":
        key = cfg.get("groq_api_key", "")
        if not key:
            raise ValueError("Groq API key not set. Add GROQ_API_KEY to Render environment variables.")
        from groq import Groq
        model  = cfg.get("groq_model", "llama-3.3-70b-versatile")
        client = Groq(api_key=key)
        resp   = client.chat.completions.create(
            model=model, messages=messages,
            max_tokens=1024, temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    elif provider == "ollama":
        try:
            import ollama as _ollama
            model = cfg.get("ollama_model", "llama3.2")
            resp  = _ollama.chat(model=model, messages=messages)
            return resp["message"]["content"].strip()
        except ImportError:
            raise ValueError("Ollama is not installed. Switch to Groq: set llm_provider=groq in config.")


def check_status() -> dict:
    """Return status dict for the /api/status endpoint."""
    api_key = os.environ.get("GROQ_API_KEY")
    cfg     = config.load_config()
    key     = api_key or cfg.get("groq_api_key", "")
    model   = os.environ.get("GROQ_MODEL") or cfg.get("groq_model", "llama-3.3-70b-versatile")

    if not key:
        return {"ok": False, "provider": "groq", "model": model,
                "error": "GROQ_API_KEY not set. Add it in Render Environment Variables."}
    try:
        from groq import Groq
        Groq(api_key=key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        return {"ok": True, "provider": "groq", "model": model, "error": ""}
    except Exception as e:
        return {"ok": False, "provider": "groq", "model": model, "error": str(e)}
