import httpx
import pytest
import respx

from simplefeed.pushover import PushoverClient

TOKEN = "test_token"
USER = "test_user"
BASE_URL = "https://api.pushover.net"


@pytest.fixture
def client():
    return PushoverClient(token=TOKEN)


class TestSendMessageValidation:
    async def test_emergency_without_retry_raises(self, client):
        with pytest.raises(ValueError, match="retry"):
            await client.send_message(USER, "msg", priority=2, expire=180)

    async def test_emergency_without_expire_raises(self, client):
        with pytest.raises(ValueError, match="expire"):
            await client.send_message(USER, "msg", priority=2, retry=30)

    async def test_emergency_without_both_raises(self, client):
        with pytest.raises(ValueError):
            await client.send_message(USER, "msg", priority=2)

    async def test_non_emergency_without_expire_does_not_raise(self, client):
        # expire=None should NOT raise for non-emergency messages
        # (this was the operator precedence bug)
        with respx.mock:
            respx.post(f"{BASE_URL}/1/messages.json").mock(
                return_value=httpx.Response(200, json={"status": 1, "request": "abc"})
            )
            result = await client.send_message(USER, "msg", priority=0)
        assert result["status"] == 1

    async def test_retry_below_30_raises(self, client):
        with pytest.raises(ValueError, match="retry must be at least 30"):
            await client.send_message(USER, "msg", priority=2, retry=29, expire=180)

    async def test_expire_above_10800_raises(self, client):
        with pytest.raises(ValueError, match="expire must be no greater than 10800"):
            await client.send_message(USER, "msg", priority=2, retry=30, expire=10801)


class TestSendMessagePayload:
    @respx.mock
    async def test_required_fields_sent(self, client):
        route = respx.post(f"{BASE_URL}/1/messages.json").mock(
            return_value=httpx.Response(200, json={"status": 1, "request": "r1"})
        )
        await client.send_message(USER, "hello")
        sent = dict(route.calls[0].request.content.decode().split("&")[i].split("=") for i in range(3))
        assert sent.get("token") == TOKEN
        assert sent.get("user") == USER

    @respx.mock
    async def test_optional_title_included_when_set(self, client):
        route = respx.post(f"{BASE_URL}/1/messages.json").mock(
            return_value=httpx.Response(200, json={"status": 1, "request": "r1"})
        )
        await client.send_message(USER, "msg", title="My Title")
        body = route.calls[0].request.content.decode()
        assert "title=My+Title" in body or "title=My%20Title" in body or "title=" in body

    @respx.mock
    async def test_emergency_payload_includes_retry_and_expire(self, client):
        route = respx.post(f"{BASE_URL}/1/messages.json").mock(
            return_value=httpx.Response(200, json={"status": 1, "request": "r1"})
        )
        await client.send_message(USER, "alert", priority=2, retry=60, expire=3600)
        body = route.calls[0].request.content.decode()
        assert "retry=60" in body
        assert "expire=3600" in body
        assert "priority=2" in body

    @respx.mock
    async def test_raises_on_http_error(self, client):
        respx.post(f"{BASE_URL}/1/messages.json").mock(
            return_value=httpx.Response(400, json={"status": 0, "errors": ["invalid token"]})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.send_message(USER, "msg")


class TestCheckReceipt:
    @respx.mock
    async def test_check_receipt_calls_correct_endpoint(self, client):
        route = respx.get(f"{BASE_URL}/1/receipts/abc123.json").mock(
            return_value=httpx.Response(200, json={"status": 1, "acknowledged": 1})
        )
        result = await client.check_receipt("abc123")
        assert result["status"] == 1
        assert route.called
