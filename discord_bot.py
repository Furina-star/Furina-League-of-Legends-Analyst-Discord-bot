"""
The main Discord bot file.
This is where the bot is initiated, the APIs are called, and the Cogs are loaded.
The main purpose of this file is to set up the architecture of the bot and handle any global events or errors that may occur.
The actual commands and logic for the draft system are handled in the Cogs.
This separate files that can be easily maintained and updated without affecting the core functionality of the bot.
This separation of concerns allows for a cleaner and more organized codebase, making it easier to debug and add new features in the future.
"""

import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import json
import requests
from riot_api import RiotAPIClient
from ai_wrapper import LeagueAI
import logging
import config

# This creates and print debugs logs properly.
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/furina.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initiate Data Dragon dictionary API  as a function
CACHE_FILE = "data/champion_cache.json"
def get_champion_mapping():
    try:
        # Fetch just the version number
        latest_version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10).json()[0]

        # Check if cache exists and is up to date
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cached_data = json.load(f)
                if cached_data.get("version") == latest_version:
                    return cached_data.get("mapping")

        # If no cache exists, or the patch updated, download the heavy file
        champ_data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json",timeout=10).json()
        id_to_name = {str(info['key']): name for name, info in champ_data['data'].items()}
        id_to_name["-1"] = "None"

        # Save the new mapping and version to the cache file
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump({"version": latest_version, "mapping": id_to_name}, f, indent=4)
        return id_to_name

    except Exception as e:
        logger.error(f"Data Dragon error: {e}")

        # Just in case the Riot Server is down (Imagine RITO????)
        if os.path.exists(CACHE_FILE):
            logger.warning("Network Failed: Falling back to old local cache.")
            with open(CACHE_FILE, "r") as f:
                return json.load(f).get("mapping", {})

        return {} # Return an empty dictionary if everything fails

# Initiate Roles from Champion_Roles.json as a function
def load_meta_roles():
    try:
        with open('data/Champion_Roles.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning("⚠️ CRITICAL: Could not find data/Champion_Roles.json!")
        return {}

# Creating a subclass of commands.Bot
class DiscordBot(commands.Bot):
    def __init__(self):
        # We set intents and turn off the default help menu here
        intents = discord.Intents.default()
        intents.message_content = False
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    # This is a special function that runs once when the bot starts up, before it connects to Discord.
    async def setup_hook(self):
        logger.info("Running one-time setup...")

        # Run the blocking Data Dragon update in a background thread
        self.champ_dict = await asyncio.to_thread(get_champion_mapping)

        # Load JSON files safely in background threads
        def load_json(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

        self.meta_db = await asyncio.to_thread(load_json, config.META_PATH)
        self.role_db = await asyncio.to_thread(load_json, config.ROLES_PATH)
        self.server_dict = config.SERVER_TO_REGION

        # Initialize APIs and AI
        self.riot_client = RiotAPIClient(config.RIOT_KEY)
        self.ai_system = LeagueAI()

        # Load Cogs (Make sure to load your new general_commands cog where /help is!)
        await self.load_extension("cogs.draft_commands")
        await self.load_extension("cogs.general_commands")
        # await self.load_extension("cogs.general_commands") # Uncomment if you made this file!

        # Sync slash commands
        logger.info("Syncing slash commands to Discord...")
        await self.tree.sync()
        logger.info("Slash commands synced successfully!")

        # Slash Command Error Handler!
        self.tree.on_error = self.on_app_command_error

    async def close(self):
        if hasattr(self, 'riot_client'):
            await self.riot_client.close()
            logger.info("Riot API connection closed safely.")
        await super().close()

    # This handle spamming and other common command errors gracefully, without crashing the bot or spamming the channel with error messages.
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            if interaction.response.is_done():
                await interaction.followup.send(f"⏳ **Slow down!** You can use this command again in `{error.retry_after:.1f}` seconds.", ephemeral=True)
            else:
                await interaction.response.send_message(f"⏳ **Slow down!** You can use this command again in `{error.retry_after:.1f}` seconds.", ephemeral=True)
        else:
            logger.error(f"Ignoring exception in slash command {interaction.command.name}:", exc_info=error)
            if interaction.response.is_done():
                await interaction.followup.send("An unexpected error occurred.", ephemeral=True)
            else:
                await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

if __name__ == "__main__":
    if not config.DISCORD_TOKEN or not config.RIOT_KEY:
        sys.exit("Error: DISCORD_TOKEN and RIOT_KEY must be set in the .env file.")

    bot = DiscordBot()

    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user.name}")
        logger.info("Furina Architecture Online and Ready!")

    bot.run(config.DISCORD_TOKEN)
