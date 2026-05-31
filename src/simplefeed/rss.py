import xml.etree.ElementTree as ET
from io import StringIO

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

    tree = ET.parse(StringIO(resp.text))

    chans: list[Channel] = []
    root = tree.getroot()
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
