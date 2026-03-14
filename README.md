# browser-mcp-server

> Full browser control for any LLM agent via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).

Powered by **Playwright** — a persistent, in-process headless Chromium session that your agent controls step-by-step.

---

## What's New in v0.3.0

- **Direct Playwright backend** — no longer shells out to the `browser-use` CLI. The browser runs in-process, reliably, with no timeout/pipe issues.
- **Always headless** — the server is designed for Docker. The `headed` parameter has been removed from all tools.
- **Element index stability** — interactive elements are stamped with `data-mcp-idx` at state-fetch time, so the index the LLM sees always maps to the correct element even after DOM updates.
- **Dependency simplified** — `browser-use` replaced by `playwright>=1.40.0`.

---

## ✨ Key Feature: Zero State Calls

Every action that changes the page (`open`, `click`, `input`, `type`, `keys`, `scroll`, `back`) **automatically returns the updated page state** in the same response. Your agent never wastes a round-trip calling `state` after an action — it's already there.

---

## Installation

### Option 1 — Docker (recommended, zero setup)

```bash
docker pull technicalheist/browser-mcp-server
```

Chromium is baked into the image — nothing else to install.

### Option 2 — pip

```bash
pip install browser-mcp-server
playwright install chromium
```

---

## Quick Start

### VS Code

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "browser-use": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "${PWD}/screenshots:/app/screenshots",
        "technicalheist/browser-mcp-server"
      ]
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "browser-use": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "${PWD}/screenshots:/app/screenshots",
        "technicalheist/browser-mcp-server"
      ]
    }
  }
}
```

### Cursor / Zed / Windsurf

```json
{
  "mcpServers": {
    "browser-use": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "${PWD}/screenshots:/app/screenshots",
        "technicalheist/browser-mcp-server"
      ]
    }
  }
}
```

> **Why Docker?** GUI apps like VS Code and Claude Desktop don't inherit your
> shell PATH, so commands installed via pip or pipx are invisible to them.
> Docker is always on the system PATH so it works everywhere, first time.

### nixagent (`mcp.json`)

```json
{
  "mcpServers": {
    "browser-use": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "${PWD}/screenshots:/app/screenshots",
        "technicalheist/browser-mcp-server"
      ],
      "active": true
    }
  }
}
```

```python
from nixagent import Agent

agent = Agent(
    name="BrowserAgent",
    system_prompt="You are a web browsing assistant.",
    mcp_config_path="mcp.json"
)
agent.run("Go to stripe.com and tell me the pricing for the Starter plan.")
```

### HTTP / Remote Agents (no Docker)

```bash
browser-mcp-server --transport streamable-http --port 8080
```

---

## Available Tools

| Tool                            | Description                                               |
| ------------------------------- | --------------------------------------------------------- |
| `browser_use_tool`              | Generic dispatcher — any browser-use command              |
| `browser_open_tool`             | Open URL →**state auto-returned**                         |
| `browser_click_tool`            | Click by index →**state auto-returned**                   |
| `browser_input_tool`            | Click + type (preferred) →**state auto-returned**         |
| `browser_type_tool`             | Type into focused element →**state auto-returned**        |
| `browser_keys_tool`             | Send keyboard key →**state auto-returned**                |
| `browser_scroll_tool`           | Scroll up/down →**state auto-returned**                   |
| `browser_back_tool`             | Navigate back →**state auto-returned**                    |
| `browser_switch_tab_tool`       | Switch tab by index →**state auto-returned**              |
| `browser_close_tab_tool`        | Close current or specific tab →**state auto-returned**    |
| `browser_hover_tool`            | Hover over element →**state auto-returned**               |
| `browser_dblclick_tool`         | Double-click element →**state auto-returned**             |
| `browser_rightclick_tool`       | Right-click element →**state auto-returned**              |
| `browser_select_tool`           | Select dropdown option →**state auto-returned**           |
| `browser_state_tool`            | Explicit state fetch*(rarely needed)*                     |
| `browser_screenshot_tool`       | Take screenshot & save to directory                       |
| `browser_get_text_tool`         | Extract element text                                      |
| `browser_get_html_tool`         | Full/scoped page HTML                                     |
| `browser_get_title_tool`        | Page title                                                |
| `browser_eval_tool`             | Execute custom JavaScript                                 |
| `browser_get_value_tool`        | Extract input or textarea value                           |
| `browser_get_attributes_tool`   | Extract all element attributes as JSON                    |
| `browser_close_tool`            | Close all sessions*(call when done)*                      |

---

## How the Auto-State Works

Traditional browser agents need two calls to interact:

```
1. agent calls: state         → get element indexes
2. agent calls: click 3       → click
3. agent calls: state         → get updated indexes  ← wasted call
4. agent calls: input 7 "..." → type
```

With `browser-mcp-server`, every mutating action returns fresh state in its own response:

```
1. agent calls: open https://...  → navigated + state returned ✓
2. agent calls: click 3           → clicked + updated state returned ✓
3. agent calls: input 7 "..."     → typed + updated state returned ✓
```

---

## CLI Reference

```
usage: browser-mcp-server [-h] [--transport {stdio,sse,streamable-http}]
                        [--host HOST] [--port PORT]

options:
  --transport   stdio | sse | streamable-http  (default: stdio)
  --host        host for HTTP transports       (default: 127.0.0.1)
  --port        port for HTTP transports       (default: 8080)
```

---

## Requirements

- **Docker** (recommended — zero setup) OR Python 3.10+ with pip
- `playwright >= 1.40.0` (installed automatically with pip; baked into Docker image)
- `mcp >= 1.0.0` (installed automatically)
- Chromium (baked into Docker image, or run `playwright install chromium` after pip install)

---

## License

MIT
