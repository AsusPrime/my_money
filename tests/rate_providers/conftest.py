from unittest.mock import AsyncMock
from unittest.mock import MagicMock


def mock_http_client(json_data):
    """A fake httpx.AsyncClient — patch httpx.AsyncClient in the module under
    test with return_value=this, so `async with httpx.AsyncClient() as client:
    await client.get(...)` returns a canned response instead of hitting the
    network."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = json_data
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client
