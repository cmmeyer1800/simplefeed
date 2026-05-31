import re

from pydantic import BaseModel, Field, model_validator


class ChannelImage(BaseModel):
    """Metadata for the channel's artwork image."""

    url: str | None
    link: str | None
    title: str | None


class Episode(BaseModel):
    """A single podcast/RSS episode."""

    title: str
    description: str = Field(repr=False)
    youtube_link: str | None = None

    @model_validator(mode="after")
    def extract_youtube_link(self) -> "Episode":
        """Populate youtube_link from the first YouTube href found in description."""
        match = re.search(
            r'href="(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^"]+)"',
            self.description,
        )
        if match:
            self.youtube_link = match.group(1)
        return self


class Channel(BaseModel):
    """A parsed RSS channel with its episodes."""

    image: ChannelImage | None
    episodes: list[Episode]
    title: str
    link: str

    def search(self, query: str) -> "Channel":
        """Return a copy of this channel whose episodes match query (case-insensitive, title or description)."""
        q = query.lower()
        matched = [
            ep
            for ep in self.episodes
            if q in ep.title.lower() or q in ep.description.lower()
        ]
        return self.model_copy(update={"episodes": matched})
