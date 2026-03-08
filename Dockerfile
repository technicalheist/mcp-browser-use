# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir build && \
    python -m build --wheel --outdir /dist

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

# Install system deps required by Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Chromium runtime libraries
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    # Font rendering
    fonts-liberation fonts-noto-color-emoji \
    # Misc
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the wheel from the builder stage
COPY --from=builder /dist/*.whl /tmp/
# Install the wheel + playwright Python package, then bake Chromium binary.
# Combined into one RUN layer so the cache is consistent.
RUN pip install --no-cache-dir /tmp/*.whl playwright && \
    python -m playwright install chromium --with-deps

# MCP servers communicate over stdio — no port needed by default
# but expose 8080 for HTTP transport mode
EXPOSE 8080

# Run in stdio mode by default (for Claude Desktop / VS Code / Cursor)
ENTRYPOINT ["browser-mcp-server"]
CMD []
