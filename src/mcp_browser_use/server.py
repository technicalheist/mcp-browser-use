"""
mcp_browser_use/server.py
──────────────────────────
FastMCP server exposing the browser-use CLI as MCP tools.

Transport options
-----------------
  stdio            — Claude Desktop, nixagent, Cursor, Zed, etc. (default)
  streamable-http  — Remote / networked agents (recommended for HTTP)
  sse              — Legacy HTTP server-sent events

Usage
-----
  # stdio (most common)
  mcp-browser-use

  # HTTP
  mcp-browser-use --transport streamable-http --port 8080

Chromium auto-install
---------------------
On first run the server checks whether the Chromium binary is present.
If it is missing it runs `playwright install chromium` automatically.
Subsequent starts skip the download entirely (binary already on disk).
"""

import argparse
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

from .tools import (
    browser_use,
    browser_open,
    browser_state,
    browser_click,
    browser_input,
    browser_type,
    browser_keys,
    browser_scroll,
    browser_back,
    browser_get_text,
    browser_get_html,
    browser_get_title,
    browser_close,
    browser_screenshot,
    browser_switch_tab,
    browser_close_tab,
    browser_hover,
    browser_dblclick,
    browser_rightclick,
    browser_select,
    browser_eval,
    browser_get_value,
    browser_get_attributes,
)

# ── Chromium auto-install ─────────────────────────────────────────────────────

def _ensure_chromium() -> None:
    """
    Check if the Playwright Chromium binary is present.
    If it is missing, download it automatically via `playwright install chromium`.

    This runs at most once — subsequent calls return immediately because
    the binary is already on disk.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415

        with sync_playwright() as p:
            executable = p.chromium.executable_path
            if os.path.exists(executable):
                return  # Already installed — nothing to do
    except Exception:
        pass  # playwright not importable or path check failed → fall through

    # Binary missing — download it now
    print(
        "[mcp-browser-use] Chromium not found. Installing automatically "
        "(one-time download, ~170 MB)...",
        file=sys.stderr,
    )
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )
    print("[mcp-browser-use] Chromium installed successfully.", file=sys.stderr)

def create_server() -> FastMCP:
    """
    Build and return the configured FastMCP server instance.
    Exposed so the server can be embedded or tested programmatically.
    """
    mcp = FastMCP(
        name="browser-use",
        instructions=(
            "Controls a persistent browser session via the browser-use CLI. "
            "After any mutating command (open, click, input, type, keys, "
            "scroll, back) the updated page state is returned automatically — "
            "never call browser_state after one of these. "
            "Always finish a task with browser_close."
        ),
    )

    # ── tool: browser_use (generic dispatcher) ────────────────────────────────
    @mcp.tool(
        description=(
            "Execute any browser-use CLI command.\n\n"
            "Mutating commands automatically return the updated page state — "
            "no need to call browser_state after them.\n\n"
            "Commands:\n"
            "  'open https://example.com'   → navigate, state auto-returned\n"
            "  'click 3'                    → click element, state auto-returned\n"
            "  'input 5 \"query\"'            → click+type, state auto-returned\n"
            "  'type \"hello\"'               → type into focused element\n"
            "  'keys \"Enter\"'               → send keyboard key\n"
            "  'scroll down' / 'scroll up'  → scroll page\n"
            "  'back'                       → navigate back\n"
            "  'get text 2'                 → extract element text\n"
            "  'get html'                   → full page HTML\n"
            "  'get html --selector \"h1\"'   → scoped HTML\n"
            "  'get title'                  → page title\n"
            "  'screenshot path.png'        → save screenshot\n"
            "  'switch 1'                   → switch tab, state auto-returned\n"
            "  'close-tab 1'                → close tab, state auto-returned\n"
            "  'hover 2'                    → hover element, state auto-returned\n"
            "  'dblclick 2'                 → double click element, state auto-returned\n"
            "  'rightclick 2'               → right click element, state auto-returned\n"
            "  'select 2 \"option\"'          → select dropdown option, state auto-returned\n"
            "  'eval \"document.title\"'      → execute javascript\n"
            "  'get value 2'                → get input/textarea value\n"
            "  'get attributes 2'           → get element attributes\n"
            "  'close --all'                → close all sessions"
        )
    )
    def browser_use_tool(command: str, headed: bool = False) -> str:
        """
        Run a browser-use CLI command.

        Args:
            command: Sub-command string (e.g. 'open https://example.com').
            headed:  Show the browser window. Only applies to 'open'. Default false.
        """
        return browser_use(command, headed=headed)

    # ── tool: browser_open ────────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Open a URL in the browser. "
            "The current page state (URL, title, clickable elements) "
            "is returned automatically."
        )
    )
    def browser_open_tool(url: str, headed: bool = False) -> str:
        """
        Navigate to a URL and return the page state.

        Args:
            url:    Full URL to open (e.g. 'https://news.ycombinator.com').
            headed: Show the browser window. Default false.
        """
        return browser_open(url, headed=headed)

    # ── tool: browser_state ───────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Get the current browser page state: URL, title, and a numbered list "
            "of all interactive elements with their indexes. "
            "Rarely needed — mutating commands already return state automatically."
        )
    )
    def browser_state_tool() -> str:
        """Explicitly fetch the current page state."""
        return browser_state()

    # ── tool: browser_click ───────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Click an element by its index (from the page state list). "
            "The updated page state is returned automatically after clicking."
        )
    )
    def browser_click_tool(index: int) -> str:
        """
        Click the element at the given index.

        Args:
            index: Element index from the page state list.
        """
        return browser_click(index)

    # ── tool: browser_input ───────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Click an element and type text into it in one step. "
            "Preferred over separate click + type. "
            "The updated page state is returned automatically."
        )
    )
    def browser_input_tool(index: int, text: str) -> str:
        """
        Click element at index, then type text.

        Args:
            index: Element index from the page state list.
            text:  Text to type.
        """
        return browser_input(index, text)

    # ── tool: browser_type ────────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Type text into the currently focused element. "
            "The updated page state is returned automatically."
        )
    )
    def browser_type_tool(text: str) -> str:
        """
        Type into the focused element.

        Args:
            text: The text to type.
        """
        return browser_type(text)

    # ── tool: browser_keys ────────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Send a keyboard key to the browser "
            "(e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown'). "
            "The updated page state is returned automatically."
        )
    )
    def browser_keys_tool(key: str) -> str:
        """
        Press a keyboard key.

        Args:
            key: Key name (e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown').
        """
        return browser_keys(key)

    # ── tool: browser_scroll ──────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Scroll the current page up or down. "
            "The updated page state is returned automatically."
        )
    )
    def browser_scroll_tool(direction: str = "down") -> str:
        """
        Scroll the page.

        Args:
            direction: 'down' or 'up'. Defaults to 'down'.
        """
        if direction not in ("up", "down"):
            return "Error: direction must be 'up' or 'down'."
        return browser_scroll(direction)

    # ── tool: browser_back ────────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Navigate back in browser history. "
            "The updated page state is returned automatically."
        )
    )
    def browser_back_tool() -> str:
        """Go back one page."""
        return browser_back()

    # ── tool: browser_get_text ────────────────────────────────────────────────
    @mcp.tool(
        description="Get the text content of a specific element by its index number."
    )
    def browser_get_text_tool(index: int) -> str:
        """
        Extract the visible text of an element.

        Args:
            index: Element index from the page state list.
        """
        return browser_get_text(index)

    # ── tool: browser_get_html ────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Get the HTML of the current page, or of a specific element "
            "using a CSS selector. Useful for scraping structured data."
        )
    )
    def browser_get_html_tool(selector: str = "") -> str:
        """
        Retrieve page HTML.

        Args:
            selector: Optional CSS selector (e.g. 'h1', '.price').
                      Leave empty for full page HTML.
        """
        return browser_get_html(selector if selector else None)

    # ── tool: browser_get_title ───────────────────────────────────────────────
    @mcp.tool(description="Get the title of the current browser page.")
    def browser_get_title_tool() -> str:
        """Return the current page title."""
        return browser_get_title()

    # ── tool: browser_close ───────────────────────────────────────────────────
    @mcp.tool(
        description=(
            "Close all browser sessions. "
            "ALWAYS call this when the task is fully complete."
        )
    )
    def browser_close_tool() -> str:
        """Close all browser sessions and end the task."""
        return browser_close()

    # ── tool: browser_screenshot ──────────────────────────────────────────────
    @mcp.tool(
        description="Take a screenshot and save it to a directory. Defaults to './screenshots'."
    )
    def browser_screenshot_tool(directory: str = "screenshots") -> str:
        """
        Take a screenshot of the current page.

        Args:
            directory: The directory to save the screenshot in. Defaults to 'screenshots'.
        """
        return browser_screenshot(directory)

    # ── tool: browser_switch_tab ──────────────────────────────────────────────
    @mcp.tool(
        description="Switch to a specific tab by its index. The updated page state is returned automatically."
    )
    def browser_switch_tab_tool(index: int) -> str:
        """Switch to a tab by index."""
        return browser_switch_tab(index)

    # ── tool: browser_close_tab ───────────────────────────────────────────────
    @mcp.tool(
        description="Close the current tab or a specific tab by index. The updated page state is returned automatically."
    )
    def browser_close_tab_tool(index: int = None) -> str:
        """Close a tab. If index is not provided, closes the current tab."""
        return browser_close_tab(index)

    # ── tool: browser_hover ───────────────────────────────────────────────────
    @mcp.tool(
        description="Hover over an element by its index. The updated page state is returned automatically."
    )
    def browser_hover_tool(index: int) -> str:
        """Hover over the element at index."""
        return browser_hover(index)

    # ── tool: browser_dblclick ────────────────────────────────────────────────
    @mcp.tool(
        description="Double-click an element by its index. The updated page state is returned automatically."
    )
    def browser_dblclick_tool(index: int) -> str:
        """Double-click the element at index."""
        return browser_dblclick(index)

    # ── tool: browser_rightclick ──────────────────────────────────────────────
    @mcp.tool(
        description="Right-click an element by its index. The updated page state is returned automatically."
    )
    def browser_rightclick_tool(index: int) -> str:
        """Right-click the element at index."""
        return browser_rightclick(index)

    # ── tool: browser_select ──────────────────────────────────────────────────
    @mcp.tool(
        description="Select a dropdown option for an element by its index. The updated page state is returned automatically."
    )
    def browser_select_tool(index: int, option: str) -> str:
        """Select a dropdown option."""
        return browser_select(index, option)

    # ── tool: browser_eval ────────────────────────────────────────────────────
    @mcp.tool(
        description="Execute JavaScript on the current page and return the result."
    )
    def browser_eval_tool(js_code: str) -> str:
        """Execute JavaScript."""
        return browser_eval(js_code)

    # ── tool: browser_get_value ───────────────────────────────────────────────
    @mcp.tool(
        description="Get the value of an input or textarea element by its index."
    )
    def browser_get_value_tool(index: int) -> str:
        """Get the value of an element at index."""
        return browser_get_value(index)

    # ── tool: browser_get_attributes ──────────────────────────────────────────
    @mcp.tool(
        description="Get all attributes of an element by its index as JSON."
    )
    def browser_get_attributes_tool(index: int) -> str:
        """Get all attributes of an element at index as JSON."""
        return browser_get_attributes(index)

    return mcp


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="browser-mcp-server",
        description="browser-use MCP server — expose browser automation to any LLM agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport modes:
  stdio            Local agents: Claude Desktop, Cursor, nixagent, Zed. (default)
  streamable-http  Modern HTTP streaming — recommended for remote agents.
  sse              Legacy HTTP server-sent events.

Examples:
  browser-mcp-server
  browser-mcp-server --transport streamable-http --port 8080
  browser-mcp-server --transport sse --host 0.0.0.0 --port 9000
        """,
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP transports (default: 8080)",
    )
    args = parser.parse_args()

    # Ensure Chromium is present before the server starts accepting requests.
    # No-op if already installed; downloads automatically on first run.
    _ensure_chromium()

    server = create_server()

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.host = args.host
        server.port = args.port
        print(
            f"[mcp-browser-use] Starting '{args.transport}' server on "
            f"http://{args.host}:{args.port}",
            file=sys.stderr,
        )
        server.run(transport=args.transport)


if __name__ == "__main__":
    main()
