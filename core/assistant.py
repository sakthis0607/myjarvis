"""
Jarvis AI Assistant - Core Engine
-----------------------------------
Handles STT, TTS, LLM calls, conversation memory, skill dispatch,
and agentic computer control via JarvisAgent.
"""
import threading
import speech_recognition as sr
import pyttsx3
import config
from core.llm import chat as llm_chat
from core.skills import match_skill
from core.license import get_current_tier, get_features
from core.agent import JarvisAgent


# Keywords that signal the user wants agentic computer control
_AGENT_TRIGGERS = [
    "open", "create", "delete", "move", "copy", "rename", "find",
    "run", "execute", "launch", "install", "list", "show me",
    "read", "write", "search", "take screenshot", "screenshot",
    "type", "press", "click", "what files", "how much", "battery",
    "cpu", "ram", "memory", "disk", "process", "kill", "close app",
    "system info", "clipboard", "paste", "folder", "directory",
]


def _should_use_agent(text: str) -> bool:
    """Decide if the request needs agentic computer control."""
    t = text.lower()
    return any(trigger in t for trigger in _AGENT_TRIGGERS)


class JarvisAssistant:
    def __init__(self, on_message=None, on_status=None):
        """
        on_message(role, text) — callback to display messages in GUI
        on_status(text)        — callback to update status bar in GUI
        """
        self.on_message = on_message or (lambda r, t: print(f"{r}: {t}"))
        self.on_status  = on_status  or (lambda t: print(f"[STATUS] {t}"))

        self._cfg     = config.load_config()
        self._history = []
        self._running = False
        self._listen_thread = None
        self._engine  = None   # lazy-initialized on first speak()
        self._tts_lock = threading.Lock()

        # STT
        self._recognizer = sr.Recognizer()

        # Agentic engine
        self._agent = JarvisAgent(
            on_thought=self._on_agent_thought,
            on_action =self._on_agent_action,
            on_result =self._on_agent_result,
            on_final  =self._on_agent_final,
        )

    # ── Voice Settings ───────────────────────────────────────────────────────

    def _apply_voice_settings(self):
        if self._engine is None:
            return
        voices = self._engine.getProperty("voices")
        idx = self._cfg.get("voice_index", 0)
        if voices and idx < len(voices):
            self._engine.setProperty("voice", voices[idx].id)
        self._engine.setProperty("rate", self._cfg.get("speech_rate", 175))

    def _get_engine(self):
        """Lazy-initialize TTS engine (safe to call from any thread)."""
        with self._tts_lock:
            if self._engine is None:
                self._engine = pyttsx3.init()
                self._apply_voice_settings()
        return self._engine

    def reload_config(self):
        self._cfg = config.load_config()
        self._apply_voice_settings()

    # ── Speak ────────────────────────────────────────────────────────────────

    def speak(self, text: str):
        self.on_message("Jarvis", text)
        try:
            engine = self._get_engine()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            self.on_status(f"TTS error: {e}")

    # ── Agent Callbacks ──────────────────────────────────────────────────────

    def _on_agent_thought(self, text: str):
        # Show thinking in chat but don't speak it (it may be JSON)
        import re, json
        # If it's a tool call JSON, show a friendly version
        match = re.search(r'\{[^{}]*"tool"\s*:[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group())
                tool = obj.get("tool", "")
                args = obj.get("args", {})
                display = f"🔧 Calling tool: {tool}  args: {args}"
                self.on_message("agent_thought", display)
                self.on_status(f"Running: {tool}...")
                return
            except Exception:
                pass
        self.on_message("agent_thought", f"💭 {text[:200]}")

    def _on_agent_action(self, name: str, args: dict):
        self.on_status(f"⚙ {name}...")
        self.on_message("agent_action", f"⚙ {name}({', '.join(f'{k}={v}' for k,v in args.items())})")

    def _on_agent_result(self, result: str):
        # Truncate long results for display
        display = result if len(result) <= 400 else result[:400] + "\n... (truncated)"
        self.on_message("agent_result", f"📋 {display}")

    def _on_agent_final(self, text: str):
        self.on_status("Ready")
        self.speak(text)
        self._add_to_history("assistant", text)

    # ── Listen (blocking) ────────────────────────────────────────────────────

    def listen_once(self) -> str:
        self.on_status("Listening...")
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.listen(source, timeout=8, phrase_time_limit=12)
            text = self._recognizer.recognize_google(audio)
            self.on_message("You", text)
            self.on_status("Processing...")
            return text.lower()
        except sr.WaitTimeoutError:
            self.on_status("Ready")
            return ""
        except sr.UnknownValueError:
            self.on_status("Ready")
            return ""
        except sr.RequestError:
            self.on_status("STT service unavailable")
            self.speak("Speech recognition service is unavailable. Check your internet.")
            return ""
        except Exception as e:
            self.on_status(f"Mic error: {e}")
            return ""

    # ── Process a command ────────────────────────────────────────────────────

    def process_command(self, user_input: str):
        if not user_input.strip():
            return

        tier     = get_current_tier()
        features = get_features()

        # 1. Check keyword skills first (fast, no LLM needed)
        skill = match_skill(user_input, tier)
        if skill:
            skill["action"](user_input, self.speak)
            return

        self._add_to_history("user", user_input)

        # 2. Route to agent if the request involves computer control
        if _should_use_agent(user_input):
            self.on_status("Agent thinking...")
            self._agent.run(user_input, history=self._history[:-1])
            return

        # 3. Plain LLM conversation fallback
        max_hist = features.get("max_history", 5)
        if len(self._history) > max_hist * 2:
            self._history = self._history[-(max_hist * 2):]

        self.on_status("Thinking...")
        try:
            messages = [
                {"role": "system", "content": self._cfg.get("system_prompt", "")}
            ] + self._history[-(max_hist * 2):]
            reply = llm_chat(messages)
            self._add_to_history("assistant", reply)
            self.speak(reply)
        except Exception as e:
            err = f"LLM error: {e}"
            self.on_status("LLM error")
            self.speak(err)
        finally:
            self.on_status("Ready")

    def _add_to_history(self, role: str, content: str):
        self._history.append({"role": role, "content": content})

    def clear_history(self):
        self._history = []
        self.on_status("Conversation cleared.")

    # ── Continuous listening loop ────────────────────────────────────────────

    def start_listening_loop(self):
        if self._running:
            return
        self._running = True
        self._listen_thread = threading.Thread(target=self._loop, daemon=True)
        self._listen_thread.start()

    def stop_listening_loop(self):
        self._running = False
        self.on_status("Voice loop stopped.")

    def _loop(self):
        self.speak("System online. How can I help you?")
        self.on_status("Ready")
        while self._running:
            user_input = self.listen_once()
            if not self._running:
                break
            if "shut down" in user_input or "goodbye" in user_input:
                self.speak("Powering down. Goodbye.")
                self._running = False
                break
            if user_input:
                self.process_command(user_input)
        self.on_status("Stopped")
