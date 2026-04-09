"""
This part of the Discord  League Analyst Bot
is all about general commands,
commands that are common between Discord Bots.
"""

import discord
from discord.ext import commands
from discord import app_commands

from utils.embed_formatter import build_help_embed


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Checks if Furina is online and functioning.")
    async def ping(self, interaction: discord.Interaction):
        # Calculate the latency in milliseconds
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"I'm online and ready to analyze! **Latency: {latency}ms**.")

    @app_commands.command(name="help", description="Displays the Furina League Analyst help menu.")
    async def help_command(self, interaction: discord.Interaction):
        from utils.embed_formatter import build_help_embed
        embed = build_help_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Setup hook to load the Cog
async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))