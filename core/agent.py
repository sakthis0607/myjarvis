"""
Jarvis - Agentic Engine
=========================
The agent receives a user goal, reasons about it using the LLM,
and executes a loop of:
  1. Think  — ask the LLM what tool to call next
  2. Act    — call the tool on the real computer
  3. Observe — feed the result back to the LLM
  4. Repeat until the LLM says it's done (no more tool calls)

The LLM communicates tool calls as JSON inside its response:
  {"tool": "run_command", "args": {"command": "dir C:\\"}}

If the LLM returns plain text with no JSON tool call, the loop ends
and that text is the final answer spoken to the user.
"""
import json
import re
import config
from core.llm import chat as llm_chat
from core.computer import TOOLS, call_tool


# ── System prompt injected for agentic mode ──────────────────────────────────

AGENT_SYSTEM_PROMPT = """You are Jarvis, an agentic AI assistant with full access to the user's Windows computer.

You can control the computer by calling tools. To call a tool, output ONLY a JSON object on a single line like this:
{{"tool": "tool_name", "args": {{"arg1": "value1", "arg2": "value2"}}}}

Available tools:
{tool_list}

Rules:
- Call ONE tool at a time. Wait for the result before calling the next.
- After getting a tool result, decide if you need another tool or if you can answer.
- When you have enough information or have completed the task, respond in plain English (no JSON).
- Be concise. Don't repeat tool results verbatim — summarize them.
- If a tool returns an error, try a different approach or explain the issue.
- Never make up file contents or command outputs — always use tools to get real data.
- For destructive actions (delete, overwrite, kill process), confirm with the user first by responding in plain English asking for confirmation.
"""

# Max agentic loop iterations to prevent infinite loops
MAX_ITERATIONS = 10


def _build_tool_list() -> str:
    lines = []
    for name, info in TOOLS.items():
        args = ", ".join(info["args"]) if info["args"] else "none"
        lines.append(f"  - {name}({args}): {info['desc']}")
    return "\n".join(lines)


def _extract_tool_call(text: str) -> dict:
    """
    Extract a JSON tool call from the LLM response.
    Handles nested braces (args object) by finding balanced { } pairs.
    Returns the parsed dict or None.
    """
    # Find all top-level JSON objects by tracking brace depth
    candidates = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start != -1:
                candidates.append(text[start:i+1])
                start = -1

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and "tool" in obj:
                # Ensure args is always a dict
                if "args" not in obj or obj["args"] is None:
                    obj["args"] = {}
                return obj
        except json.JSONDecodeError:
            continue

    return None


class JarvisAgent:
    def __init__(self, on_thought=None, on_action=None, on_result=None, on_final=None):
        """
        Callbacks for the GUI to display agent activity:
          on_thought(text)  — LLM reasoning / tool decision
          on_action(name, args) — tool being called
          on_result(result) — tool output
          on_final(text)    — final answer to speak
        """
        self.on_thought = on_thought or (lambda t: print(f"[THINK] {t}"))
        self.on_action  = on_action  or (lambda n, a: print(f"[ACT]   {n}({a})"))
        self.on_result  = on_result  or (lambda r: print(f"[OBS]   {r}"))
        self.on_final   = on_final   or (lambda t: print(f"[DONE]  {t}"))

        self._system_prompt = AGENT_SYSTEM_PROMPT.format(
            tool_list=_build_tool_list()
        )

    def run(self, goal: str, history: list = None) -> str:
        """
        Run the agentic loop for a given goal.
        Returns the final answer string.
        """
        # Build message history
        messages = [{"role": "system", "content": self._system_prompt}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": goal})

        for iteration in range(MAX_ITERATIONS):
            # ── Think ────────────────────────────────────────────────────────
            try:
                llm_text = llm_chat(messages)
            except Exception as e:
                final = f"LLM error: {e}"
                self.on_final(final)
                return final

            self.on_thought(llm_text)

            # ── Check for tool call ──────────────────────────────────────────
            tool_call = _extract_tool_call(llm_text)

            if tool_call is None:
                self.on_final(llm_text)
                return llm_text

            # ── Act ──────────────────────────────────────────────────────────
            tool_name = tool_call.get("tool", "")
            tool_args = tool_call.get("args", {})

            self.on_action(tool_name, tool_args)
            messages.append({"role": "assistant", "content": llm_text})

            # ── Execute tool ─────────────────────────────────────────────────
            result = call_tool(tool_name, tool_args)
            result_text = result["result"] if result["ok"] else f"ERROR: {result['error']}"

            self.on_result(result_text)
            messages.append({
                "role": "user",
                "content": f"Tool result for {tool_name}:\n{result_text}"
            })

        final = "I reached the maximum number of steps. Please try a more specific request."
        self.on_final(final)
        return final
