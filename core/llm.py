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
    messages: list of {"role": "user"|"assistant"|"system", "content": str}
    """
    cfg      = config.load_config()
    provider = os.environ.get("LLM_PROVIDER") or cfg.get("llm_provider", "groq")

    if provider == "groq":
        client = _get_groq_client()
        model  = os.environ.get("GROQ_MODEL") or cfg.get("groq_model", "llama-3.3-70b-versatile")
        resp   = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    elif provider == "ollama":
        import ollama as _ollama
        model  = cfg.get("ollama_model", "llama3.2")
        resp   = _ollama.chat(model=model, messages=messages)
        return resp["message"]["content"].strip()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'groq' or 'ollama'.")


def check_status() -> dict:
    """Return status dict for the /api/status endpoint."""
    cfg      = config.load_config()
    provider = os.environ.get("LLM_PROVIDER") or cfg.get("llm_provider", "groq")

    if provider == "groq":
        model = os.environ.get("GROQ_MODEL") or cfg.get("groq_model", "llama-3.3-70b-versatile")
        try:
            chat([{"role": "user", "content": "hi"}])
            return {"ok": True, "provider": "groq", "model": model, "error": ""}
        except Exception as e:
            return {"ok": False, "provider": "groq", "model": model, "error": str(e)}

    elif provider == "ollama":
        model = cfg.get("ollama_model", "llama3.2")
        try:
            import ollama as _ollama
            _ollama.chat(model=model, messages=[{"role": "user", "content": "hi"}])
            return {"ok": True, "provider": "ollama", "model": model, "error": ""}
        except Exception as e:
            return {"ok": False, "provider": "ollama", "model": model, "error": str(e)}

    return {"ok": False, "provider": provider, "model": "", "error": "Unknown provider"}
