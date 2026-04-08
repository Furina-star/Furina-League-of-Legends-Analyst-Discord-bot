"""
This part of the Discord  League Analyst Bot
is all about general commands,
commands that are common between Discord Bots.
"""

import discord
from discord.ext import commands

from utils.embed_formatter import build_help_embed


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def ping(self, ctx):
        await ctx.send("I'm online and ready to analyze!")

    @commands.command(name="help")
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def custom_help(self, ctx):
        embed = build_help_embed()

        await ctx.send(embed=embed)

# Setup hook to load the Cog
async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))