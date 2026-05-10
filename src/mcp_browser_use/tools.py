"""
mcp_browser_use/tools.py
─────────────────────────
Async Playwright implementation for browser control.

FastMCP runs tool handlers inside an asyncio event loop, so we must use
playwright.async_api throughout. All public functions are async.

Auto-state behaviour
────────────────────
Every command that mutates the page (open, click, input, type, keys, scroll,
back) automatically fetches and appends the current state to its output.
"""

import json
import os
import shlex
import time
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# ── Persistent in-process browser session ────────────────────────────────────

_pw = None
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_pages: list = []   # list[Page]
_cur: int = 0       # index of the currently active tab


async def _launch() -> None:
    """Start Playwright and launch Chromium (always headless) if not already running."""
    global _pw, _browser, _context, _pages, _cur
    if _pw is None:
        _pw = await async_playwright().start()
    if _browser is None or not _browser.is_connected():
        _browser = await _pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage"],
        )
        _context = None
        _pages = []
        _cur = 0
    if _context is None:
        _context = await _browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )


async def _page() -> Page:
    """Return the currently active page, creating one if needed."""
    global _pages, _cur
    await _launch()
    if not _pages:
        _pages.append(await _context.new_page())
        _cur = 0
    if _pages[_cur].is_closed():
        _pages.pop(_cur)
        _cur = max(0, _cur - 1)
        if not _pages:
            _pages.append(await _context.new_page())
            _cur = 0
    return _pages[_cur]


# ── Element indexing via data-mcp-idx stamps ──────────────────────────────────

_SELECTOR = (
    "a[href], button, input, select, textarea, "
    "[role='button'], [role='link'], [role='checkbox'], "
    "[role='radio'], [role='menuitem'], [role='option'], "
    "[role='tab'], [role='combobox'], [onclick]"
)

_STAMP_SCRIPT = """(sel) => {
    const els = Array.from(document.querySelectorAll(sel));
    const results = [];
    let idx = 0;
    for (const el of els) {
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) continue;
        el.dataset.mcpIdx = String(idx);
        results.push({
            index: idx,
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.value || el.placeholder
                   || el.getAttribute('aria-label') || '').trim().substring(0, 120),
            type: el.type || el.getAttribute('role') || '',
            href: el.getAttribute('href') || '',
            name: el.getAttribute('name') || '',
        });
        idx++;
    }
    return results;
}"""


async def _stamp(pg: Page) -> list:
    """Inject data-mcp-idx into all visible interactive elements; return info list."""
    return await pg.evaluate(_STAMP_SCRIPT, _SELECTOR)


async def _el(index: int):
    """Locator for the element stamped with the given index."""
    pg = await _page()
    return pg.locator(f"[data-mcp-idx='{index}']")


# ── State helpers ─────────────────────────────────────────────────────────────

async def _state_str() -> str:
    pg = await _page()
    url = pg.url
    title = await pg.title()
    items = await _stamp(pg)
    lines = [f"URL: {url}", f"Title: {title}", "", "Interactive elements:"]
    for el in items:
        label = el["text"] or el["href"] or el["name"] or el["type"] or el["tag"]
        kind = el["type"] or el["tag"]
        lines.append(f"  [{el['index']}] <{el['tag']}> ({kind}) {label}")
    return "\n".join(lines)


async def _with_state(msg: str) -> str:
    try:
        return f"{msg}\n\n[auto-state]\n{await _state_str()}"
    except Exception as exc:
        return f"{msg}\n\n[auto-state failed: {exc}]"


# ── Primary dispatcher ────────────────────────────────────────────────────────

async def browser_use(command: str) -> str:
    """
    Run any browser-use command.

    Mutating commands (open, click, input, type, keys, scroll, back)
    automatically append the updated page state to their output.
    """
    parts = command.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    if sub == "open":
        return await browser_open(rest)
    if sub == "click":
        return await browser_click(int(rest))
    if sub == "input":
        p = shlex.split(rest)
        return await browser_input(int(p[0]), p[1] if len(p) > 1 else "")
    if sub == "type":
        return await browser_type(rest.strip('"'))
    if sub == "keys":
        return await browser_keys(rest.strip('"'))
    if sub == "scroll":
        return await browser_scroll(rest or "down")
    if sub == "back":
        return await browser_back()
    if sub == "state":
        return await browser_state()
    if sub == "screenshot":
        return await browser_screenshot(rest or "screenshots")
    if sub == "switch":
        return await browser_switch_tab(int(rest))
    if sub == "close-tab":
        return await browser_close_tab(int(rest) if rest else None)
    if sub == "hover":
        return await browser_hover(int(rest))
    if sub == "dblclick":
        return await browser_dblclick(int(rest))
    if sub == "rightclick":
        return await browser_rightclick(int(rest))
    if sub == "select":
        p = shlex.split(rest)
        return await browser_select(int(p[0]), p[1] if len(p) > 1 else "")
    if sub == "eval":
        return await browser_eval(rest.strip('"'))
    if sub == "get":
        p = rest.split(maxsplit=1)
        what = p[0].lower() if p else ""
        arg = p[1].strip() if len(p) > 1 else ""
        if what == "text":
            return await browser_get_text(int(arg))
        if what == "html":
            sel = None
            if "--selector" in arg:
                sel = arg.split("--selector", 1)[1].strip().strip('"')
            return await browser_get_html(sel)
        if what == "title":
            return await browser_get_title()
        if what == "value":
            return await browser_get_value(int(arg))
        if what == "attributes":
            return await browser_get_attributes(int(arg))
        raise ValueError(f"Unknown get sub-command: {what!r}")
    if sub == "close":
        return await browser_close()
    raise ValueError(f"Unknown command: {sub!r}")


# ── Convenience wrappers ──────────────────────────────────────────────────────

async def browser_open(url: str) -> str:
    """Open a URL. Page state is returned automatically."""
    await _launch()
    pg = await _page()
    await pg.goto(url, wait_until="domcontentloaded", timeout=60_000)
    return await _with_state(f"Opened: {url}")


async def browser_state() -> str:
    """Get the current page state (URL, title, element list)."""
    return await _state_str()


async def browser_click(index: int) -> str:
    """Click the element at index. Page state auto-returned."""
    loc = await _el(index)
    await loc.click()
    pg = await _page()
    await pg.wait_for_load_state("domcontentloaded")
    return await _with_state(f"Clicked element [{index}]")


async def browser_input(index: int, text: str) -> str:
    """Click element at index then type text. Page state auto-returned."""
    loc = await _el(index)
    await loc.click()
    await loc.fill(text)
    return await _with_state(f"Input '{text}' into element [{index}]")


async def browser_type(text: str) -> str:
    """Type into the currently focused element. Page state auto-returned."""
    pg = await _page()
    await pg.keyboard.type(text)
    return await _with_state(f"Typed: {text!r}")


async def browser_keys(key: str) -> str:
    """Send a keyboard key (e.g. 'Enter'). Page state auto-returned."""
    pg = await _page()
    await pg.keyboard.press(key)
    await pg.wait_for_load_state("domcontentloaded")
    return await _with_state(f"Keys: {key!r}")


async def browser_scroll(direction: str = "down") -> str:
    """Scroll up or down. Page state auto-returned."""
    assert direction in ("up", "down"), "direction must be 'up' or 'down'"
    delta = 400 if direction == "down" else -400
    pg = await _page()
    await pg.evaluate(f"window.scrollBy(0, {delta})")
    return await _with_state(f"Scrolled {direction}")


async def browser_back() -> str:
    """Navigate back. Page state auto-returned."""
    pg = await _page()
    await pg.go_back(wait_until="domcontentloaded")
    return await _with_state("Navigated back")


async def browser_get_text(index: int) -> str:
    """Get the text content of the element at index."""
    loc = await _el(index)
    return await loc.inner_text()


async def browser_get_html(selector: Optional[str] = None) -> str:
    """Get full page HTML, or HTML of a specific CSS selector."""
    pg = await _page()
    if selector:
        return await pg.locator(selector).inner_html()
    return await pg.content()


async def browser_get_title() -> str:
    """Get the current page title."""
    pg = await _page()
    return await pg.title()


async def browser_close() -> str:
    """Close all browser sessions. Call when the task is done."""
    global _pw, _browser, _context, _pages, _cur
    if _context:
        await _context.close()
        _context = None
    if _browser:
        await _browser.close()
        _browser = None
    if _pw:
        await _pw.stop()
        _pw = None
    _pages = []
    _cur = 0
    return "All browser sessions closed."


async def browser_screenshot(path_or_dir: str = "screenshots") -> str:
    """Take a screenshot and save it."""
    _, ext = os.path.splitext(path_or_dir)
    if ext.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        filepath = path_or_dir
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    else:
        os.makedirs(path_or_dir, exist_ok=True)
        filepath = os.path.join(path_or_dir, f"{int(time.time())}.png")
    pg = await _page()
    await pg.screenshot(path=filepath)
    return f"Screenshot saved to: {filepath}"


async def browser_switch_tab(index: int) -> str:
    """Switch to a specific tab by index. Page state auto-returned."""
    global _cur
    if index >= len(_pages):
        raise ValueError(f"Tab index {index} out of range (found {len(_pages)} tabs)")
    _cur = index
    return await _with_state(f"Switched to tab [{index}]")


async def browser_close_tab(index: Optional[int] = None) -> str:
    """Close the current tab or a specific tab by index. Page state auto-returned."""
    global _pages, _cur
    target = index if index is not None else _cur
    if target >= len(_pages):
        raise ValueError(f"Tab index {target} out of range")
    await _pages[target].close()
    _pages.pop(target)
    if _cur >= len(_pages):
        _cur = max(0, len(_pages) - 1)
    if _pages:
        return await _with_state(f"Closed tab [{target}]")
    return f"Closed tab [{target}]. No tabs remaining."


async def browser_hover(index: int) -> str:
    """Hover over the element at index. Page state auto-returned."""
    loc = await _el(index)
    await loc.hover()
    return await _with_state(f"Hovered element [{index}]")


async def browser_dblclick(index: int) -> str:
    """Double-click the element at index. Page state auto-returned."""
    loc = await _el(index)
    await loc.dblclick()
    return await _with_state(f"Double-clicked element [{index}]")


async def browser_rightclick(index: int) -> str:
    """Right-click the element at index. Page state auto-returned."""
    loc = await _el(index)
    await loc.click(button="right")
    return await _with_state(f"Right-clicked element [{index}]")


async def browser_select(index: int, option: str) -> str:
    """Select a dropdown option. Page state auto-returned."""
    loc = await _el(index)
    await loc.select_option(label=option)
    return await _with_state(f"Selected '{option}' in element [{index}]")


async def browser_eval(js_code: str) -> str:
    """Execute JavaScript and return the result."""
    pg = await _page()
    result = await pg.evaluate(js_code)
    return json.dumps(result, ensure_ascii=False, default=str)


async def browser_get_value(index: int) -> str:
    """Get the value of an input or textarea element at index."""
    loc = await _el(index)
    return await loc.input_value()


async def browser_get_attributes(index: int) -> str:
    """Get all attributes of the element at index as JSON."""
    pg = await _page()
    attrs = await pg.evaluate(
        """(idx) => {
            const el = document.querySelector('[data-mcp-idx="' + idx + '"]');
            if (!el) return {};
            const attrs = {};
            for (const a of el.attributes) attrs[a.name] = a.value;
            return attrs;
        }""",
        index,
    )
    return json.dumps(attrs, ensure_ascii=False)

