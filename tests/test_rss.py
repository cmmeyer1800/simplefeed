import httpx
import respx

from simplefeed.rss import parse_rss_feed

FEED_URL = "https://feeds.example.com/podcast.xml"


def _rss(channel_xml: str) -> str:
    return f"<?xml version='1.0'?><rss version='2.0'><channel>{channel_xml}</channel></rss>"


MINIMAL_CHANNEL = _rss(
    "<title>My Podcast</title>"
    "<link>https://example.com</link>"
    "<item><title>Episode 1</title><description>First ep</description></item>"
    "<item><title>Episode 2</title><description>Second ep</description></item>"
)

CHANNEL_WITH_IMAGE = _rss(
    "<title>Art Podcast</title>"
    "<link>https://art.example.com</link>"
    "<image>"
    "  <url>https://art.example.com/cover.jpg</url>"
    "  <title>Art Podcast</title>"
    "  <link>https://art.example.com</link>"
    "</image>"
    "<item><title>Ep</title><description>desc</description></item>"
)

CHANNEL_MISSING_TITLE = _rss(
    "<link>https://example.com</link>"
    "<item><title>Ep</title><description>desc</description></item>"
)

CHANNEL_ITEM_MISSING_TITLE = _rss(
    "<title>My Podcast</title>"
    "<link>https://example.com</link>"
    "<item><description>No title here</description></item>"
    "<item><title>Good Ep</title><description>Fine</description></item>"
)


@respx.mock
async def test_returns_channel_with_episodes():
    respx.get(FEED_URL).mock(return_value=httpx.Response(200, text=MINIMAL_CHANNEL))
    channels = await parse_rss_feed(FEED_URL)
    assert len(channels) == 1
    assert channels[0].title == "My Podcast"
    assert channels[0].link == "https://example.com"
    assert len(channels[0].episodes) == 2
    assert channels[0].episodes[0].title == "Episode 1"


@respx.mock
async def test_parses_channel_image():
    respx.get(FEED_URL).mock(return_value=httpx.Response(200, text=CHANNEL_WITH_IMAGE))
    channels = await parse_rss_feed(FEED_URL)
    img = channels[0].image
    assert img is not None
    assert img.url == "https://art.example.com/cover.jpg"
    assert img.title == "Art Podcast"


@respx.mock
async def test_channel_without_image_is_none():
    respx.get(FEED_URL).mock(return_value=httpx.Response(200, text=MINIMAL_CHANNEL))
    channels = await parse_rss_feed(FEED_URL)
    assert channels[0].image is None


@respx.mock
async def test_non_200_returns_empty():
    respx.get(FEED_URL).mock(return_value=httpx.Response(404))
    channels = await parse_rss_feed(FEED_URL)
    assert channels == []


@respx.mock
async def test_channel_missing_title_is_skipped():
    respx.get(FEED_URL).mock(
        return_value=httpx.Response(200, text=CHANNEL_MISSING_TITLE)
    )
    channels = await parse_rss_feed(FEED_URL)
    assert channels == []


@respx.mock
async def test_item_missing_title_is_skipped():
    respx.get(FEED_URL).mock(
        return_value=httpx.Response(200, text=CHANNEL_ITEM_MISSING_TITLE)
    )
    channels = await parse_rss_feed(FEED_URL)
    assert len(channels[0].episodes) == 1
    assert channels[0].episodes[0].title == "Good Ep"


@respx.mock
async def test_parses_non_ascii_utf8_bytes():
    xml = _rss(
        "<title>Café Cast ☕</title>"
        "<link>https://example.com</link>"
        "<item><title>Episode 🎙️ naïve</title><description>Ünïcödé 😀</description></item>"
    )
    respx.get(FEED_URL).mock(
        return_value=httpx.Response(200, content=xml.encode("utf-8"))
    )
    channels = await parse_rss_feed(FEED_URL)
    assert channels[0].title == "Café Cast ☕"
    assert channels[0].episodes[0].title == "Episode 🎙️ naïve"
    assert channels[0].episodes[0].description == "Ünïcödé 😀"


@respx.mock
async def test_honours_xml_encoding_declaration():
    xml = (
        "<?xml version='1.0' encoding='ISO-8859-1'?><rss version='2.0'><channel>"
        "<title>Café</title><link>https://example.com</link>"
        "<item><title>Épisode</title><description>d</description></item>"
        "</channel></rss>"
    )
    respx.get(FEED_URL).mock(
        return_value=httpx.Response(200, content=xml.encode("iso-8859-1"))
    )
    channels = await parse_rss_feed(FEED_URL)
    assert channels[0].title == "Café"
    assert channels[0].episodes[0].title == "Épisode"


@respx.mock
async def test_youtube_link_extracted_in_episode():
    xml = _rss(
        "<title>Video Cast</title>"
        "<link>https://example.com</link>"
        "<item>"
        "  <title>Watch This</title>"
        '  <description>&lt;a href="https://youtu.be/abc123"&gt;Watch&lt;/a&gt;</description>'
        "</item>"
    )
    respx.get(FEED_URL).mock(return_value=httpx.Response(200, text=xml))
    channels = await parse_rss_feed(FEED_URL)
    assert channels[0].episodes[0].youtube_link == "https://youtu.be/abc123"
