# ⚡ Jarvis AI Assistant

A local AI voice assistant with a modern GUI, conversation memory, skill system, and license-based monetization.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Make sure Ollama is running with llama3.2
ollama run llama3.2

# 3. Launch the app
python jarvis_app.py
```

---

## 💰 Monetization Tiers

| Feature              | Free | Pro  | Enterprise |
|----------------------|------|------|------------|
| Voice commands       | ✅   | ✅   | ✅         |
| Conversation memory  | 5    | 50   | 500        |
| Browser skills       | ✅   | ✅   | ✅         |
| Developer tools      | ❌   | ✅   | ✅         |
| Custom skills        | ❌   | ✅   | ✅         |
| Priority support     | ❌   | ❌   | ✅         |

**Suggested pricing:**
- Free — $0 (lead magnet)
- Pro — $9.99/month or $49 one-time
- Enterprise — $29.99/month or $149 one-time

---

## 🔑 Generating License Keys (Seller Only)

```bash
# Generate 1 Pro key expiring Dec 31, 2026
python license_generator.py --tier PRO --expiry 20261231

# Generate 10 Enterprise keys
python license_generator.py --tier ENT --expiry 20271231 --count 10
```

**Keep `license_generator.py` and `core/license.py` private.**  
Change `_SECRET` in `core/license.py` before distributing.

---

## 🗣️ Voice Commands

| Say...                        | Action                  |
|-------------------------------|-------------------------|
| "open YouTube"                | Opens YouTube           |
| "search YouTube for [query]"  | Searches YouTube        |
| "search Google for [query]"   | Searches Google         |
| "what time is it"             | Tells current time      |
| "open VS Code" *(Pro)*        | Launches VS Code        |
| "open terminal" *(Pro)*       | Opens command prompt    |
| "open calculator"             | Opens calculator        |
| "shut down" / "goodbye"       | Exits voice loop        |
| *anything else*               | Answered by AI (Ollama) |

---

## 📦 Packaging as .exe (for selling)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Jarvis" jarvis_app.py
```

The `.exe` will be in the `dist/` folder. Distribute that to customers.

---

## 🛒 Where to Sell

- [Gumroad](https://gumroad.com) — easiest setup, instant payouts
- [Lemon Squeezy](https://lemonsqueezy.com) — better for subscriptions
- [Product Hunt](https://producthunt.com) — for launch visibility
- Upwork / Fiverr — for custom builds ($500–$5000)
