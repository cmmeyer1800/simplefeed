
from simplefeed.models import Channel, ChannelImage, Episode
from simplefeed.server import _render, _title_hash


def make_channel(
    title="Test Podcast",
    link="https://example.com",
    image=None,
    episodes=None,
) -> Channel:
    return Channel(
        title=title,
        link=link,
        image=image,
        episodes=episodes or [],
    )


def make_episode(title="Episode 1", description="A description.", youtube_link=None) -> Episode:
    ep = Episode(title=title, description=description)
    if youtube_link:
        ep.youtube_link = youtube_link
    return ep


class TestTitleHash:
    def test_returns_hex_string(self):
        h = _title_hash("Hello")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_same_title_same_hash(self):
        assert _title_hash("Ep 1") == _title_hash("Ep 1")

    def test_different_titles_different_hashes(self):
        assert _title_hash("Ep 1") != _title_hash("Ep 2")


class TestRender:
    def test_renders_channel_title(self):
        ch = make_channel(title="My Podcast")
        out = _render(ch, "")
        assert "My Podcast" in out

    def test_renders_episode_titles(self):
        ch = make_channel(episodes=[make_episode("Deep Dive into asyncio")])
        out = _render(ch, "")
        assert "Deep Dive into asyncio" in out

    def test_renders_youtube_link_when_present(self):
        ep = make_episode()
        ep.youtube_link = "https://youtu.be/abc"
        ch = make_channel(episodes=[ep])
        out = _render(ch, "")
        assert "https://youtu.be/abc" in out
        assert "Watch on YouTube" in out

    def test_no_youtube_link_when_absent(self):
        ch = make_channel(episodes=[make_episode()])
        out = _render(ch, "")
        assert "Watch on YouTube" not in out

    def test_search_query_shown_in_subtitle(self):
        ch = make_channel()
        out = _render(ch, "fastapi")
        assert "fastapi" in out

    def test_empty_episodes_shows_no_episodes_found(self):
        ch = make_channel(episodes=[])
        out = _render(ch, "")
        assert "No episodes found" in out

    def test_episode_count_in_subtitle(self):
        eps = [make_episode(f"Ep {i}") for i in range(3)]
        ch = make_channel(episodes=eps)
        out = _render(ch, "")
        assert "3 episodes" in out

    def test_single_episode_no_plural(self):
        ch = make_channel(episodes=[make_episode()])
        out = _render(ch, "")
        assert "1 episode" in out
        assert "1 episodes" not in out

    def test_image_tag_rendered_when_image_present(self):
        img = ChannelImage(url="https://example.com/art.jpg", link=None, title=None)
        ch = make_channel(image=img)
        out = _render(ch, "")
        assert '<img src="/image"' in out

    def test_no_image_tag_when_image_absent(self):
        ch = make_channel(image=None)
        out = _render(ch, "")
        assert '<img src="/image"' not in out

    def test_xss_query_is_escaped(self):
        ch = make_channel()
        out = _render(ch, '<script>alert(1)</script>')
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_xss_episode_title_is_escaped(self):
        ep = make_episode(title='<script>alert("xss")</script>')
        ch = make_channel(episodes=[ep])
        out = _render(ch, "")
        assert "<script>" not in out

    def test_xss_channel_title_is_escaped(self):
        ch = make_channel(title='<b onclick="bad()">Title</b>')
        out = _render(ch, "")
        assert '<b onclick' not in out

    def test_channel_link_in_header(self):
        ch = make_channel(link="https://mypodcast.example.com")
        out = _render(ch, "")
        assert "https://mypodcast.example.com" in out
