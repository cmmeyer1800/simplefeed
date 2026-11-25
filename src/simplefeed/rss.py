import xml.etree.ElementTree as ET

import httpx

from simplefeed.models import Channel, ChannelImage, Episode


async def parse_rss_feed(url: str) -> list[Channel]:
    """Fetch and parse an RSS feed URL, returning one Channel per <channel> element."""

    def get_attr_or(item: ET.Element, attr: str) -> str | None:
        elem = item.find(attr)
        return None if elem is None else elem.text

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        return []

    # Parse the raw bytes, not resp.text. The production feed is ~7 MB and contains
    # emoji, so resp.text is a ~29 MB str (4 bytes/char) and StringIO makes a second
    # copy. Those ~30 MB transient buffers fragment glibc's heap, and RSS grew ~6 MB
    # per poll until the pod was OOMKilled every few hours. Parsing bytes keeps the
    # transient at the feed's size, and ElementTree honours the XML encoding declaration.
    root = ET.fromstring(resp.content)

    chans: list[Channel] = []
    for channel in root.findall("./channel"):
        chan_title = get_attr_or(channel, "title")
        chan_link = get_attr_or(channel, "link")
        if chan_title is None or chan_link is None:
            continue

        image = channel.find("image")
        chan_image = (
            ChannelImage(
                url=get_attr_or(image, "url"),
                title=get_attr_or(image, "title"),
                link=get_attr_or(image, "link"),
            )
            if image is not None
            else None
        )

        eps: list[Episode] = []
        for item in channel.findall("./item"):
            title = get_attr_or(item, "title")
            desc = get_attr_or(item, "description")
            if title is None or desc is None:
                continue
            eps.append(Episode(title=title, description=desc))

        chans.append(
            Channel(
                image=chan_image,
                episodes=eps,
                title=chan_title,
                link=chan_link,
            )
        )

    return chans
