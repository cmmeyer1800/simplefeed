
from simplefeed.models import Channel, ChannelImage, Episode


def make_channel(**overrides) -> Channel:
    defaults = dict(
        title="My Podcast",
        link="https://example.com",
        image=None,
        episodes=[],
    )
    return Channel(**{**defaults, **overrides})


def make_episode(**overrides) -> Episode:
    defaults = dict(title="Episode 1", description="No links here.")
    return Episode(**{**defaults, **overrides})


class TestEpisode:
    def test_youtube_link_extracted_watch_url(self):
        ep = Episode(
            title="EP",
            description='<a href="https://www.youtube.com/watch?v=abc123">Watch</a>',
        )
        assert ep.youtube_link == "https://www.youtube.com/watch?v=abc123"

    def test_youtube_link_extracted_short_url(self):
        ep = Episode(
            title="EP",
            description='<a href="https://youtu.be/abc123">Watch</a>',
        )
        assert ep.youtube_link == "https://youtu.be/abc123"

    def test_youtube_link_extracted_without_www(self):
        ep = Episode(
            title="EP",
            description='<a href="https://youtube.com/watch?v=xyz">Watch</a>',
        )
        assert ep.youtube_link == "https://youtube.com/watch?v=xyz"

    def test_no_youtube_link_when_absent(self):
        ep = Episode(title="EP", description='<a href="https://example.com">link</a>')
        assert ep.youtube_link is None

    def test_no_youtube_link_for_plain_text(self):
        ep = Episode(title="EP", description="Just some text, no links.")
        assert ep.youtube_link is None

    def test_first_youtube_link_used_when_multiple(self):
        ep = Episode(
            title="EP",
            description=(
                '<a href="https://youtu.be/first">a</a>'
                '<a href="https://youtu.be/second">b</a>'
            ),
        )
        assert ep.youtube_link == "https://youtu.be/first"

    def test_explicit_youtube_link_field_overridden_by_validator(self):
        # model_validator runs after field assignment, so the extracted value wins
        ep = Episode(
            title="EP",
            description='<a href="https://youtu.be/fromDesc">Watch</a>',
            youtube_link="https://youtu.be/ignored",
        )
        assert ep.youtube_link == "https://youtu.be/fromDesc"


class TestChannel:
    def _channel_with_episodes(self, *titles: str) -> Channel:
        eps = [
            Episode(title=t, description=f"Description for {t}") for t in titles
        ]
        return make_channel(episodes=eps)

    def test_search_matches_title(self):
        ch = self._channel_with_episodes("Python Tips", "JavaScript Tricks")
        result = ch.search("python")
        assert len(result.episodes) == 1
        assert result.episodes[0].title == "Python Tips"

    def test_search_matches_description(self):
        eps = [
            Episode(title="Ep 1", description="Covers asyncio in detail"),
            Episode(title="Ep 2", description="About web frameworks"),
        ]
        ch = make_channel(episodes=eps)
        result = ch.search("asyncio")
        assert len(result.episodes) == 1
        assert result.episodes[0].title == "Ep 1"

    def test_search_case_insensitive(self):
        ch = self._channel_with_episodes("FASTAPI Deep Dive")
        assert len(ch.search("fastapi").episodes) == 1
        assert len(ch.search("FASTAPI").episodes) == 1
        assert len(ch.search("FastAPI").episodes) == 1

    def test_search_empty_query_returns_all(self):
        ch = self._channel_with_episodes("Ep 1", "Ep 2", "Ep 3")
        result = ch.search("")
        assert len(result.episodes) == 3

    def test_search_no_match_returns_empty(self):
        ch = self._channel_with_episodes("Python Tips", "JavaScript Tricks")
        result = ch.search("ruby")
        assert result.episodes == []

    def test_search_returns_copy_not_mutation(self):
        ch = self._channel_with_episodes("Ep 1", "Ep 2")
        filtered = ch.search("Ep 1")
        assert len(ch.episodes) == 2  # original unchanged
        assert len(filtered.episodes) == 1

    def test_search_preserves_channel_metadata(self):
        ch = make_channel(
            title="My Feed",
            link="https://feed.example.com",
            episodes=[Episode(title="Ep", description="desc")],
        )
        result = ch.search("Ep")
        assert result.title == "My Feed"
        assert result.link == "https://feed.example.com"


class TestChannelImage:
    def test_all_fields_optional(self):
        img = ChannelImage(url=None, link=None, title=None)
        assert img.url is None
        assert img.link is None
        assert img.title is None

    def test_fields_stored(self):
        img = ChannelImage(
            url="https://example.com/img.png",
            link="https://example.com",
            title="My Podcast",
        )
        assert img.url == "https://example.com/img.png"
        assert img.title == "My Podcast"
