"""
mcp_browser_use/tools.py
─────────────────────────
Thin wrapper around the `browser-use` CLI.

Auto-state behaviour
────────────────────
Every command that mutates the page (open, click, input, type, keys, scroll,
back) automatically fetches and appends `browser-use state` to its output.
The LLM therefore NEVER needs to call `state` explicitly — it always has the
current element list in the response of the previous action.
"""

import subprocess
from typing import Optional


# Commands that mutate the page → state is auto-appended after each of these.
_MUTATING_CMDS = {"open", "click", "input", "type", "keys", "scroll", "back"}


# ── Low-level runner ──────────────────────────────────────────────────────────

def _run(args: list[str], timeout: int = 30) -> str:
    """Run `browser-use <args>` and return stdout+stderr. Raises on failure."""
    cmd = ["browser-use"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(
                f"browser-use failed (exit {result.returncode}):\n{output}"
            )
        return output
    except FileNotFoundError:
        raise RuntimeError(
            "browser-use CLI not found. "
            "Install it with: pip install browser-use && playwright install"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"browser-use timed out after {timeout}s: {' '.join(cmd)}"
        )


# ── Primary dispatcher ────────────────────────────────────────────────────────

def browser_use(command: str, headed: bool = False) -> str:
    """
    Run any browser-use CLI command.

    Mutating commands (open, click, input, type, keys, scroll, back)
    automatically append the updated page state to their output so the LLM
    never needs an explicit `state` call after an action.
    """
    parts = command.strip().split(maxsplit=1)
    sub_cmd = parts[0].lower() if parts else ""

    args: list[str] = []
    if headed and sub_cmd == "open":
        args.append("--headed")
    args += command.strip().split()

    output = _run(args)

    if sub_cmd in _MUTATING_CMDS:
        label = f"browser-use: after '{sub_cmd}' — current state (auto-fetched)"
        try:
            state_output = _run(["state"])
            output = f"{output}\n\n[{label}]\n{state_output}"
        except RuntimeError as exc:
            output += f"\n\n[browser-use: state fetch failed — {exc}]"

    return output


# ── Convenience wrappers ──────────────────────────────────────────────────────

def browser_open(url: str, headed: bool = False) -> str:
    """Open a URL. Page state is returned automatically."""
    return browser_use(f"open {url}", headed=headed)

def browser_state() -> str:
    """Get the current page state (URL, title, element list)."""
    return _run(["state"])

def browser_click(index: int) -> str:
    """Click the element at index. Page state auto-returned."""
    return browser_use(f"click {index}")

def browser_input(index: int, text: str) -> str:
    """Click element at index then type text. Page state auto-returned."""
    return browser_use(f'input {index} "{text}"')

def browser_type(text: str) -> str:
    """Type into the currently focused element. Page state auto-returned."""
    return browser_use(f'type "{text}"')

def browser_keys(key: str) -> str:
    """Send a keyboard key (e.g. 'Enter'). Page state auto-returned."""
    return browser_use(f'keys "{key}"')

def browser_scroll(direction: str = "down") -> str:
    """Scroll up or down. Page state auto-returned."""
    assert direction in ("up", "down"), "direction must be 'up' or 'down'"
    return browser_use(f"scroll {direction}")

def browser_back() -> str:
    """Navigate back. Page state auto-returned."""
    return browser_use("back")

def browser_get_text(index: int) -> str:
    """Get the text content of the element at index."""
    return browser_use(f"get text {index}")

def browser_get_html(selector: Optional[str] = None) -> str:
    """Get full page HTML, or HTML of a specific CSS selector."""
    if selector:
        return browser_use(f'get html --selector "{selector}"')
    return browser_use("get html")

def browser_get_title() -> str:
    """Get the current page title."""
    return browser_use("get title")

def browser_close() -> str:
    """Close all browser sessions. Call when the task is done."""
    return browser_use("close --all")
