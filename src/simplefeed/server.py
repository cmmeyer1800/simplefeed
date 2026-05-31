import asyncio
import hashlib
import html
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from simplefeed.models import Channel
from simplefeed.pushover import PushoverClient
from simplefeed.rss import parse_rss_feed
from simplefeed.settings import settings

logger = logging.getLogger(__name__)

_channel: Channel
_image_bytes: bytes = b""
_image_content_type: str = "image/jpeg"
_known_hashes: set[str] = set()


def _title_hash(title: str) -> str:
    """Return a stable SHA-256 hex digest used to identify episodes by title."""
    return hashlib.sha256(title.encode()).hexdigest()


async def _poll_feed() -> None:
    """Background loop: re-fetch the feed on each interval and push notifications for new episodes."""
    global _channel, _known_hashes
    async with PushoverClient(settings.PUSHOVER_TOKEN) as pushover:
        while True:
            await asyncio.sleep(settings.REFRESH_INTERVAL)
            try:
                channels = await parse_rss_feed(settings.RSS_FEED.encoded_string())
            except Exception:
                logger.exception("Failed to fetch RSS feed")
                continue

            if not channels:
                continue

            new_channel = channels[0]
            new_episodes = [
                ep for ep in new_channel.episodes
                if _title_hash(ep.title) not in _known_hashes
            ]

            for ep in new_episodes:
                _known_hashes.add(_title_hash(ep.title))
                for user in settings.PUSHOVER_USERS:
                    try:
                        await pushover.send_message(
                            user,
                            message=ep.title,
                            title=f"New episode: {new_channel.title}",
                        )
                    except Exception:
                        logger.exception("Failed to send Pushover notification to %s", user)

            _channel = new_channel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load feed, cache channel art, seed known hashes, start poll loop. Shutdown: cancel loop."""
    global _channel, _image_bytes, _image_content_type, _known_hashes
    channels = await parse_rss_feed(settings.RSS_FEED.encoded_string())
    if not channels:
        raise RuntimeError("No channels found — check the feed URL")
    _channel = channels[0]

    _known_hashes = {_title_hash(ep.title) for ep in _channel.episodes}

    if _channel.image and _channel.image.url:
        async with httpx.AsyncClient() as client:
            resp = await client.get(_channel.image.url)
            if resp.status_code == 200:
                _image_bytes = resp.content
                _image_content_type = resp.headers.get("content-type", "image/jpeg")

    poll_task = asyncio.create_task(_poll_feed())
    yield
    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/image")
async def image():
    """Serve the cached channel artwork."""
    return Response(content=_image_bytes, media_type=_image_content_type)


def _render(channel: Channel, query: str) -> str:
    """Render the episode browser page as an HTML string."""
    episode_cards = ""
    for ep in channel.episodes:
        yt = ""
        if ep.youtube_link:
            yt = f'<a class="yt" href="{html.escape(ep.youtube_link)}" target="_blank">▶ Watch on YouTube</a>'
        episode_cards += f"""
        <div class="card">
            <h3>{html.escape(ep.title)}</h3>
            {yt}
        </div>"""

    image_html = ""
    if channel.image and channel.image.url:
        image_html = f'<img src="/image" alt="{html.escape(channel.title)}">'

    count = len(channel.episodes)
    subtitle = f"{count} episode{'s' if count != 1 else ''}" + (f' matching <em>"{html.escape(query)}"</em>' if query else "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(channel.title)}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #f5f5f5; color: #222; }}
  header {{ background: #111; color: #fff; padding: 1.5rem 2rem; display: flex; align-items: center; gap: 1.25rem; }}
  header img {{ width: 64px; height: 64px; border-radius: 8px; object-fit: cover; }}
  header h1 {{ font-size: 1.4rem; }}
  header a {{ color: #aaa; font-size: .85rem; text-decoration: none; }}
  .toolbar {{ padding: 1.25rem 2rem; display: flex; align-items: center; gap: 1rem; background: #fff; border-bottom: 1px solid #e0e0e0; }}
  .toolbar input {{ flex: 1; padding: .55rem .9rem; border: 1px solid #ccc; border-radius: 6px; font-size: 1rem; }}
  .toolbar button {{ padding: .55rem 1.2rem; background: #111; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; }}
  .subtitle {{ padding: .75rem 2rem; font-size: .9rem; color: #666; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; padding: 1rem 2rem 2rem; }}
  .card {{ background: #fff; border-radius: 8px; padding: 1.1rem 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card h3 {{ font-size: .95rem; line-height: 1.4; margin-bottom: .6rem; }}
  .yt {{ display: inline-block; font-size: .82rem; color: #c00; text-decoration: none; font-weight: 600; }}
  .yt:hover {{ text-decoration: underline; }}
  .empty {{ padding: 3rem 2rem; text-align: center; color: #888; }}
</style>
</head>
<body>
<header>
  {image_html}
  <div>
    <h1>{html.escape(channel.title)}</h1>
    <a href="{html.escape(channel.link)}" target="_blank">{html.escape(channel.link)}</a>
  </div>
</header>
<div class="toolbar">
  <form method="get" style="display:contents">
    <input name="q" type="search" placeholder="Search episodes…" value="{html.escape(query)}" autofocus>
    <button type="submit">Search</button>
  </form>
</div>
<div class="subtitle">{subtitle}</div>
{"<div class='grid'>" + episode_cards + "</div>" if channel.episodes else "<div class='empty'>No episodes found.</div>"}
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index(q: str = ""):
    """Episode browser: optionally filter by search query."""
    result = _channel.search(q) if q else _channel
    return _render(result, q)


def run(host: str = "127.0.0.1", port: int = 8000):
    """Start the uvicorn server."""
    uvicorn.run(app, host=host, port=port)
