import httpx

_MESSAGES_ENDPOINT = "messages.json"
_RECEIPTS_ENDPOINT = "receipts/{receipt}.json"


class PushoverClient(httpx.AsyncClient):
    """Async Pushover API client backed by httpx.AsyncClient.

    Use as an async context manager:
        async with PushoverClient(token) as client:
            await client.send_message(user, message="hello")
    """

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.pushover.net",
        api_version: int = 1,
    ) -> None:
        self.token = token
        super().__init__(base_url=f"{base_url}/{api_version}/")

    async def send_message(
        self,
        user: str,
        message: str,
        *,
        title: str | None = None,
        url: str | None = None,
        url_title: str | None = None,
        retry: int | None = None,
        expire: int | None = None,
        priority: int = 0,
        sound: str | None = None,
        device: str | None = None,
        html: bool = False,
        timestamp: int | None = None,
        ttl: int | None = None,
        attachment_base64: str | None = None,
        attachment_type: str | None = None,
    ) -> dict:
        """Send a Pushover notification and return the API response dict.

        Raises ValueError for invalid priority-2 (emergency) constraints.
        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        if priority == 2 and (retry is None or expire is None):
            raise ValueError(
                "Emergency notifications (priority=2) require both retry and expire"
            )

        payload: dict = {"token": self.token, "user": user, "message": message}

        if title is not None:
            payload["title"] = title
        if url is not None:
            payload["url"] = url
        if url_title is not None:
            payload["url_title"] = url_title
        if priority != 0:
            payload["priority"] = priority
        if sound is not None:
            payload["sound"] = sound
        if device is not None:
            payload["device"] = device
        if html:
            payload["html"] = 1
        if timestamp is not None:
            payload["timestamp"] = timestamp
        if ttl is not None:
            payload["ttl"] = ttl
        if attachment_base64 is not None:
            payload["attachment_base64"] = attachment_base64
        if attachment_type is not None:
            payload["attachment_type"] = attachment_type
        if retry is not None:
            if retry < 30:
                raise ValueError("retry must be at least 30 seconds")
            payload["retry"] = retry
        if expire is not None:
            if expire > 10800:
                raise ValueError("expire must be no greater than 10800 seconds")
            payload["expire"] = expire

        response = await self.post(_MESSAGES_ENDPOINT, data=payload)
        response.raise_for_status()
        return response.json()

    async def check_receipt(self, receipt: str) -> dict:
        """Return the delivery receipt report for an emergency notification."""
        response = await self.get(
            _RECEIPTS_ENDPOINT.format(receipt=receipt),
            params={"token": self.token},
        )
        response.raise_for_status()
        return response.json()
