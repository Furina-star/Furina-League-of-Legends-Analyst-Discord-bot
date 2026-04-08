import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.draft_commands import DraftCommands

# Sets up a fake bot, fake Riot API, and fake AI for testing.
@pytest.fixture
def setup_cog():
    mock_bot = MagicMock()
    mock_riot = AsyncMock()
    mock_ai = MagicMock()

    # Initialize the Cog with our fake systems and empty dictionaries
    cog = DraftCommands(mock_bot, mock_riot, mock_ai, meta_db={}, champ_dict={})
    cog.server_dict = {"na1": "americas"}
    return cog, mock_riot, mock_ai

# Creates a fake Discord context (ctx) to simulate a user sending a message.
@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.typing = MagicMock()
    ctx.typing.return_value.__aenter__ = AsyncMock()
    ctx.typing.return_value.__aexit__ = AsyncMock()
    return ctx

# What happens if the user searches for a player that doesn't exist?
@pytest.mark.asyncio
async def test_predict_error_branch_player_not_found(setup_cog, mock_ctx):
    cog, mock_riot, _ = setup_cog

    # Force the fake Riot API to return None (simulating "Player Not Found")
    mock_riot.get_puuid.return_value = None

    # Run the command exactly how a user would trigger it
    await cog.predict(cog, mock_ctx, server="na1", full_riot_id="Ghost#NA1")

    # Assert (Verify) that the bot sent the correct error message to the channel
    # Because we called ctx.send twice (once for "Fetching..." and once for the error),
    mock_ctx.send.assert_any_call("⚠️ Could not find player Ghost #NA1 on NA1. Check spelling!")

# What happens if the player exists, but isn't in a match?
@pytest.mark.asyncio
async def test_predict_error_branch_not_in_game(setup_cog, mock_ctx):
    cog, mock_riot, _ = setup_cog

    # Force Riot API to find the player, but fail to find a live match
    mock_riot.get_puuid.return_value = "fake-puuid-123"
    mock_riot.get_live_match.return_value = None

    # Run the command
    await cog.predict(cog, mock_ctx, server="na1", full_riot_id="RealPlayer#NA1")

    # Verify the bot sent the "not in a live match" error!
    mock_ctx.send.assert_any_call("⚠️ This player is not currently in a live match!")