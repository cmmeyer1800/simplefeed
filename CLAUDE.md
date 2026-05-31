# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the server
uv run python main.py

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Add a dependency
uv add <package>
```

## Architecture

`simplefeed` is a single-page FastAPI app that polls one RSS feed, serves an episode browser at `/`, and sends Pushover push notifications when new episodes appear.

**Data flow:**
1. On startup (`lifespan` in `server.py`), the feed is fetched once, the channel image is downloaded and cached as bytes, and all existing episode title hashes are pre-loaded into `_known_hashes` so they don't trigger notifications.
2. A background `asyncio` task (`_poll_feed`) re-fetches the feed every `REFRESH_INTERVAL` seconds. Episodes whose title hash isn't in `_known_hashes` are treated as new and trigger Pushover messages.
3. The single in-memory `_channel` global is replaced each poll cycle. There is no database.

**Module roles:**
- `models.py` — Pydantic models (`Channel`, `Episode`, `ChannelImage`). `Episode.extract_youtube_link` parses a YouTube URL from the description HTML. `Channel.search` returns a filtered copy.
- `rss.py` — Fetches and parses RSS XML via `httpx` + stdlib `xml.etree`. Returns `list[Channel]`; currently only `channels[0]` is used.
- `server.py` — FastAPI app, background poll loop, and server-side HTML rendering (no JS templating engine; plain f-strings).
- `pushover.py` — Async Pushover client extending `httpx.AsyncClient`. Handles priority-2 emergency notification constraints (retry/expire required, capped at 10800 s).
- `settings.py` — `pydantic-settings` config loaded from `.env`. `RSS_FEED` is validated as `AnyHttpUrl`; `PUSHOVER_USERS` is a JSON list of user keys.

**Configuration (`.env`):**

| Variable | Description |
|---|---|
| `RSS_FEED` | URL of the RSS feed to monitor |
| `PUSHOVER_TOKEN` | Pushover application token |
| `PUSHOVER_USERS` | JSON array of Pushover user keys |
| `REFRESH_INTERVAL` | Poll interval in seconds (default 300) |
