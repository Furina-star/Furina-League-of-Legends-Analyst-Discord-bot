"""
This cog is responsible for handling commands regarding about leaderboards and such.
Adding more future implementation I hope.
"""

import discord
from discord.ext import commands
from discord import app_commands
from modules.interface.embed_formatter import build_hall_of_shame_embed
from discord.app_commands import locale_str as _
from modules.utils.constants import CMD_HALLOFSHAME, DESC_HALLOFSHAME

class LeaderboardCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name=_(CMD_HALLOFSHAME), description=_(DESC_HALLOFSHAME))
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    async def hallofshame(self, interaction: discord.Interaction):
        guild = interaction.guild
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        assert guild is not None

        await interaction.response.defer()

        # Fetch the IDs of everyone currently in their specific server
        server_member_ids = [str(member.id) for member in guild.members]
        stats = await self.bot.db.get_hall_of_shame(server_member_ids)

        embed = build_hall_of_shame_embed(stats, guild)

        # Send the finalized execution warrant
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardCommands(bot))