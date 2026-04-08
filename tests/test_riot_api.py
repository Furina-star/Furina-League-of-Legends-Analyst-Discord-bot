import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from riot_api import RiotAPIClient


# The @pytest.mark.asyncio tells pytest that this test uses async/await
@pytest.mark.asyncio
async def test_get_puuid_mocked():
    # Set up a client with a fake API key
    client = RiotAPIClient(api_key="FAKE_KEY")

    # Patch (Mock) the _fetch method so it never actually connects to the internet
    with patch.object(client, '_fetch', new_callable=AsyncMock) as mock_fetch:
        # Tell the fake server exactly what JSON to return
        mock_fetch.return_value = {"puuid": "fake-puuid-12345"}

        # Run the function
        result = await client.get_puuid("Hide on bush", "KR1")

        # Assert (Verify) the results!
        assert result == "fake-puuid-12345"
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_get_champion_mastery_bot_bouncer():
    client = RiotAPIClient(api_key="FAKE_KEY")

    # Test that passing 'None' (a bot) returns 0 mastery immediately without fetching
    with patch.object(client, '_fetch', new_callable=AsyncMock) as mock_fetch:
        result = await client.get_champion_mastery(None, 85)

        assert result == 0
        mock_fetch.assert_not_called()  # It should have bounced before fetching!


@pytest.mark.asyncio
async def test_fetch_retry_behavior_on_5xx():
    client = RiotAPIClient(api_key="FAKE_KEY")

    # Create fake responses
    error_response = MagicMock()
    error_response.status = 503  # Riot Server is dying!

    success_response = AsyncMock()
    success_response.status = 200  # Riot Server recovered!
    success_response.json.return_value = {"status": "success"}

    # This mock_get will simulate the server responses: first two attempts fail with 503, then the third attempt succeeds with 200
    mock_get = AsyncMock()
    mock_get.return_value.__aenter__.side_effect = [
        error_response,  # Attempt 1: Fails
        error_response,  # Attempt 2: Fails
        success_response  # Attempt 3: Succeeds!
    ]

    # This patches the aiohttp.ClientSession.get method to use our mock_get instead, simulating the server responses
    with patch('riot_api.aiohttp.ClientSession.get', new=mock_get):
        with patch('riot_api.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._fetch("https://fake-url.com")

            # Did it eventually return the success data?
            assert result == {"status": "success"}
            assert mock_get.call_count == 3
            assert mock_sleep.call_count == 2