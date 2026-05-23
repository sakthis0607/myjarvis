"""
Jarvis - Computer Control Tools
"""
import os
import subprocess
import shutil
import platform
import datetime
import webbrowser
from pathlib import Path

# Windows-only / desktop-only imports — safe to fail on Linux/cloud
try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

try:
    import pyperclip
    _HAS_CLIPBOARD = True
except ImportError:
    _HAS_CLIPBOARD = False

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    import pyautogui
    _HAS_GUI = True
except Exception:
    _HAS_GUI = False


def _ok(result: str) -> dict:
    return {"ok": True, "result": result, "error": ""}

def _err(error: str) -> dict:
    return {"ok": False, "result": "", "error": error}


# ── Smart App Launcher ────────────────────────────────────────────────────────

# Known exe names for common apps
_APP_ALIASES = {
    "whatsapp":      ["WhatsApp.exe"],
    "telegram":      ["Telegram.exe"],
    "discord":       ["Discord.exe"],
    "chrome":        ["chrome.exe"],
    "firefox":       ["firefox.exe"],
    "edge":          ["msedge.exe"],
    "word":          ["WINWORD.EXE"],
    "excel":         ["EXCEL.EXE"],
    "powerpoint":    ["POWERPNT.EXE"],
    "notepad":       ["notepad.exe"],
    "calculator":    ["CalculatorApp.exe", "calc.exe"],
    "paint":         ["mspaint.exe"],
    "vlc":           ["vlc.exe"],
    "zoom":          ["Zoom.exe"],
    "teams":         ["Teams.exe"],
    "slack":         ["slack.exe"],
    "vscode":        ["Code.exe"],
    "vs code":       ["Code.exe"],
    "spotify":       ["Spotify.exe"],
    "steam":         ["steam.exe"],
    "obs":           ["obs64.exe"],
    "taskmgr":       ["Taskmgr.exe"],
    "task manager":  ["Taskmgr.exe"],
    "file explorer": ["explorer.exe"],
    "explorer":      ["explorer.exe"],
    "control panel": ["control.exe"],
    "instagram":     ["Instagram.exe"],
    "netflix":       ["Netflix.exe"],
    "skype":         ["Skype.exe"],
    "snipping tool": ["SnippingTool.exe"],
    "paint 3d":      ["PaintStudio4.exe"],
    "photos":        ["Microsoft.Photos.exe"],
}

# Directories to search for .exe files
_SEARCH_DIRS = [
    os.environ.get("LOCALAPPDATA", ""),
    os.environ.get("APPDATA", ""),
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps"),
]

# UWP / ms-protocol shortcuts
_UWP_PROTOCOLS = {
    "settings":      "ms-settings:",
    "store":         "ms-windows-store:",
    "mail":          "outlookmail:",
    "calendar":      "outlookcal:",
    "photos":        "ms-photos:",
    "maps":          "bingmaps:",
    "calculator":    "calculator:",
    "weather":       "bingweather:",
    "news":          "bingnews:",
    "xbox":          "xbox:",
    "feedback hub":  "feedback-hub:",
}


def _try_store_app(app_name: str) -> bool:
    """
    Use PowerShell to find a Store/UWP app by name and launch it
    via its AppUserModelId. This is the most reliable method for
    apps like WhatsApp, Instagram, Netflix, etc.
    """
    ps_script = (
        f"$app = Get-AppxPackage | "
        f"Where-Object {{$_.Name -like '*{app_name}*'}} | "
        f"Select-Object -First 1; "
        f"if ($app) {{"
        f"  $manifest = Get-AppxPackageManifest $app.PackageFullName; "
        f"  $appId = $manifest.Package.Applications.Application[0].Id; "
        f"  if (-not $appId) {{ $appId = $manifest.Package.Applications.Application.Id }}; "
        f"  $aumid = $app.PackageFamilyName + '!' + $appId; "
        f"  Start-Process \"shell:AppsFolder\\$aumid\"; "
        f"  Write-Output \"launched:$aumid\" "
        f"}} else {{ Write-Output 'not_found' }}"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        return output.startswith("launched:")
    except Exception:
        return False


def _find_exe_on_disk(exe_name: str) -> str:
    """Walk common install dirs to find an executable."""
    for base in _SEARCH_DIRS:
        if not base or not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower() == exe_name.lower():
                    return os.path.join(root, f)
            # Limit search depth
            if root[len(base):].count(os.sep) >= 4:
                dirs.clear()
    return ""


def open_application(app_name: str) -> dict:
    """
    Launch any application on Windows using 4 strategies in order:
    1. ms-protocol (Settings, Calculator, etc.)
    2. PowerShell Store/UWP app lookup (WhatsApp, Instagram, etc.)
    3. Direct exe launch from PATH or known locations
    4. Windows 'start' command fallback
    """
    name = app_name.lower().strip()

    # 1. ms-protocol shortcuts
    for key, protocol in _UWP_PROTOCOLS.items():
        if key in name:
            try:
                os.startfile(protocol)
                return _ok(f"Opened {app_name}.")
            except Exception:
                pass

    # 2. PowerShell Store app lookup — works for WhatsApp, Instagram, etc.
    # Build search term: use the raw name, strip "open"/"launch" if present
    search_term = name.replace("open ", "").replace("launch ", "").replace("start ", "").strip()
    if _try_store_app(search_term):
        return _ok(f"Opened {app_name} (Store app).")

    # 3. Direct exe launch
    candidates = []
    for alias, exes in _APP_ALIASES.items():
        if alias in name or name in alias:
            candidates.extend(exes)
    if not candidates:
        # Guess: treat the app name itself as an exe
        candidates = [search_term + ".exe", search_term]

    for exe in candidates:
        # Try direct (works if in PATH or WindowsApps)
        try:
            subprocess.Popen(exe, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return _ok(f"Launched {exe}.")
        except Exception:
            pass
        # Try finding on disk
        if exe.endswith(".exe"):
            path = _find_exe_on_disk(exe)
            if path:
                try:
                    subprocess.Popen([path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return _ok(f"Launched {path}.")
                except Exception:
                    pass

    # 4. Windows 'start' fallback
    try:
        subprocess.Popen(f'start "" "{search_term}"', shell=True)
        return _ok(f"Attempted to open {app_name}.")
    except Exception as e:
        return _err(f"Could not open '{app_name}'. Is it installed? ({e})")


# ── File System ───────────────────────────────────────────────────────────────

def list_directory(path: str = ".") -> dict:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return _err(f"Path does not exist: {path}")
        items = []
        for item in sorted(p.iterdir()):
            kind = "DIR " if item.is_dir() else "FILE"
            size = f"  ({item.stat().st_size:,} bytes)" if item.is_file() else ""
            items.append(f"[{kind}] {item.name}{size}")
        return _ok("\n".join(items) if items else "(empty directory)")
    except Exception as e:
        return _err(str(e))


def read_file(path: str) -> dict:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return _err(f"File not found: {path}")
        if p.stat().st_size > 500_000:
            return _err("File too large (>500KB).")
        return _ok(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return _err(str(e))


def write_file(path: str, content: str) -> dict:
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return _ok(f"Written {len(content)} chars to {p}")
    except Exception as e:
        return _err(str(e))


def append_file(path: str, content: str) -> dict:
    try:
        p = Path(path).expanduser().resolve()
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
        return _ok(f"Appended to {p}")
    except Exception as e:
        return _err(str(e))


def delete_file(path: str) -> dict:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return _err(f"Not found: {path}")
        p.unlink()
        return _ok(f"Deleted: {p}")
    except Exception as e:
        return _err(str(e))


def create_folder(path: str) -> dict:
    try:
        Path(path).expanduser().resolve().mkdir(parents=True, exist_ok=True)
        return _ok(f"Folder created: {path}")
    except Exception as e:
        return _err(str(e))


def copy_file(src: str, dst: str) -> dict:
    try:
        shutil.copy2(src, dst)
        return _ok(f"Copied {src} to {dst}")
    except Exception as e:
        return _err(str(e))


def move_file(src: str, dst: str) -> dict:
    try:
        shutil.move(src, dst)
        return _ok(f"Moved {src} to {dst}")
    except Exception as e:
        return _err(str(e))


def search_files(pattern: str, directory: str = ".") -> dict:
    try:
        base = Path(directory).expanduser().resolve()
        matches = list(base.rglob(pattern))[:50]
        return _ok("\n".join(str(m) for m in matches) if matches else "No files found.")
    except Exception as e:
        return _err(str(e))


def find_in_files(text: str, directory: str = ".", extension: str = "*") -> dict:
    try:
        base = Path(directory).expanduser().resolve()
        results = []
        for f in base.rglob(f"*.{extension}"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                if text.lower() in content.lower():
                    lines = [f"  Line {i+1}: {l.strip()}"
                             for i, l in enumerate(content.splitlines())
                             if text.lower() in l.lower()]
                    results.append(f"{f}:\n" + "\n".join(lines[:5]))
            except Exception:
                continue
            if len(results) >= 20:
                break
        return _ok("\n\n".join(results) if results else "No matches found.")
    except Exception as e:
        return _err(str(e))


# ── Shell / Process ───────────────────────────────────────────────────────────

def run_command(command: str, cwd: str = None, timeout: int = 30) -> dict:
    try:
        r = subprocess.run(command, shell=True, capture_output=True,
                           text=True, timeout=timeout, cwd=cwd or os.getcwd())
        out = r.stdout.strip()
        err = r.stderr.strip()
        return _ok((out + ("\n[stderr]: " + err if err else "")) or "(no output)")
    except subprocess.TimeoutExpired:
        return _err(f"Timed out after {timeout}s")
    except Exception as e:
        return _err(str(e))


def list_processes() -> dict:
    try:
        procs = []
        for p in sorted(psutil.process_iter(["pid", "name", "memory_info"]),
                        key=lambda x: x.info["name"] or ""):
            try:
                mb = p.info["memory_info"].rss / 1024 / 1024
                procs.append(f"PID {p.info['pid']:>6}  {p.info['name']:<35} {mb:>7.1f} MB")
            except Exception:
                continue
        return _ok("\n".join(procs[:60]))
    except Exception as e:
        return _err(str(e))


def kill_process(name_or_pid: str) -> dict:
    try:
        try:
            pid = int(name_or_pid)
            p = psutil.Process(pid)
            name = p.name()
            p.terminate()
            return _ok(f"Terminated {name} (PID {pid})")
        except ValueError:
            pass
        killed = []
        for p in psutil.process_iter(["pid", "name"]):
            if name_or_pid.lower() in (p.info["name"] or "").lower():
                p.terminate()
                killed.append(f"{p.info['name']} (PID {p.info['pid']})")
        return _ok(f"Terminated: {', '.join(killed)}") if killed else _err(f"No process: {name_or_pid}")
    except Exception as e:
        return _err(str(e))


# ── System Info ───────────────────────────────────────────────────────────────

def get_system_info() -> dict:
    try:
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        return _ok(
            f"OS:       {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"CPU:      {cpu}% used  ({psutil.cpu_count()} cores)\n"
            f"RAM:      {ram.used/1e9:.1f} GB / {ram.total/1e9:.1f} GB  ({ram.percent}%)\n"
            f"Disk C:   {disk.used/1e9:.1f} GB / {disk.total/1e9:.1f} GB  ({disk.percent}%)\n"
            f"Time:     {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as e:
        return _err(str(e))


def get_battery() -> dict:
    try:
        b = psutil.sensors_battery()
        if b is None:
            return _ok("No battery (desktop PC).")
        return _ok(f"Battery: {b.percent:.0f}%  |  {'Charging' if b.power_plugged else 'Discharging'}")
    except Exception as e:
        return _err(str(e))


# ── Clipboard ─────────────────────────────────────────────────────────────────

def get_clipboard() -> dict:
    try:
        return _ok(pyperclip.paste() or "(empty)")
    except Exception as e:
        return _err(str(e))


def set_clipboard(text: str) -> dict:
    try:
        pyperclip.copy(text)
        return _ok(f"Copied to clipboard.")
    except Exception as e:
        return _err(str(e))


# ── Screen / Input ────────────────────────────────────────────────────────────

def take_screenshot(save_path: str = None) -> dict:
    try:
        if not save_path:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = str(Path.home() / "Desktop" / f"screenshot_{ts}.png")
        pyautogui.screenshot().save(save_path)
        return _ok(f"Screenshot saved: {save_path}")
    except Exception as e:
        return _err(str(e))


def type_text(text: str) -> dict:
    try:
        import time; time.sleep(0.5)
        pyautogui.typewrite(text, interval=0.03)
        return _ok(f"Typed: {text[:60]}")
    except Exception as e:
        return _err(str(e))


def press_key(key: str) -> dict:
    try:
        keys = [k.strip() for k in key.split("+")]
        pyautogui.hotkey(*keys) if len(keys) > 1 else pyautogui.press(keys[0])
        return _ok(f"Pressed: {key}")
    except Exception as e:
        return _err(str(e))


def move_mouse(x: int, y: int) -> dict:
    try:
        pyautogui.moveTo(x, y, duration=0.3)
        return _ok(f"Mouse at ({x}, {y})")
    except Exception as e:
        return _err(str(e))


def click_mouse(x: int = None, y: int = None, button: str = "left") -> dict:
    try:
        pyautogui.click(x, y, button=button) if x and y else pyautogui.click(button=button)
        return _ok(f"Clicked {button} at ({x}, {y})")
    except Exception as e:
        return _err(str(e))


def get_screen_size() -> dict:
    try:
        w, h = pyautogui.size()
        return _ok(f"{w} x {h} pixels")
    except Exception as e:
        return _err(str(e))


# ── Web ───────────────────────────────────────────────────────────────────────

def open_url(url: str) -> dict:
    try:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return _ok(f"Opened: {url}")
    except Exception as e:
        return _err(str(e))


# ── Tool Registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "list_directory":   {"fn": list_directory,   "desc": "List files/folders in a directory",          "args": ["path"]},
    "read_file":        {"fn": read_file,         "desc": "Read contents of a text file",               "args": ["path"]},
    "write_file":       {"fn": write_file,        "desc": "Write/create a file with given content",     "args": ["path", "content"]},
    "append_file":      {"fn": append_file,       "desc": "Append text to an existing file",            "args": ["path", "content"]},
    "delete_file":      {"fn": delete_file,       "desc": "Delete a file",                              "args": ["path"]},
    "create_folder":    {"fn": create_folder,     "desc": "Create a folder",                            "args": ["path"]},
    "copy_file":        {"fn": copy_file,         "desc": "Copy a file",                                "args": ["src", "dst"]},
    "move_file":        {"fn": move_file,         "desc": "Move or rename a file",                      "args": ["src", "dst"]},
    "search_files":     {"fn": search_files,      "desc": "Search files by glob pattern",               "args": ["pattern", "directory"]},
    "find_in_files":    {"fn": find_in_files,     "desc": "Search for text inside files",               "args": ["text", "directory", "extension"]},
    "run_command":      {"fn": run_command,       "desc": "Run a shell/CMD command",                    "args": ["command", "cwd", "timeout"]},
    "open_application": {"fn": open_application,  "desc": "Open any installed app by name (WhatsApp, Chrome, etc.)", "args": ["app_name"]},
    "list_processes":   {"fn": list_processes,    "desc": "List running processes",                     "args": []},
    "kill_process":     {"fn": kill_process,      "desc": "Kill a process by name or PID",              "args": ["name_or_pid"]},
    "get_system_info":  {"fn": get_system_info,   "desc": "Get CPU/RAM/disk/OS info",                   "args": []},
    "get_battery":      {"fn": get_battery,       "desc": "Get battery status",                         "args": []},
    "get_clipboard":    {"fn": get_clipboard,     "desc": "Read clipboard content",                     "args": []},
    "set_clipboard":    {"fn": set_clipboard,     "desc": "Write text to clipboard",                    "args": ["text"]},
    "take_screenshot":  {"fn": take_screenshot,   "desc": "Take a screenshot",                          "args": ["save_path"]},
    "type_text":        {"fn": type_text,         "desc": "Type text into focused window",              "args": ["text"]},
    "press_key":        {"fn": press_key,         "desc": "Press a key/hotkey e.g. ctrl+c",             "args": ["key"]},
    "move_mouse":       {"fn": move_mouse,        "desc": "Move mouse to coordinates",                  "args": ["x", "y"]},
    "click_mouse":      {"fn": click_mouse,       "desc": "Click mouse at coordinates",                 "args": ["x", "y", "button"]},
    "get_screen_size":  {"fn": get_screen_size,   "desc": "Get screen resolution",                      "args": []},
    "open_url":         {"fn": open_url,          "desc": "Open a URL in the browser",                  "args": ["url"]},
}


def call_tool(name: str, args: dict) -> dict:
    if name not in TOOLS:
        return _err(f"Unknown tool: {name}. Available: {', '.join(TOOLS.keys())}")
    try:
        return TOOLS[name]["fn"](**args)
    except TypeError as e:
        return _err(f"Bad args for {name}: {e}")
    except Exception as e:
        return _err(f"Tool error ({name}): {e}")
