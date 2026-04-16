"""
This is the live tracker where it auto-detects when a linked player enters a live match and broadcasts it in a specific channel with the prediction and draft board.
It runs every 3 minutes and checks all linked accounts against the Riot Spectator API.
If it finds a new live match, it extracts the teams, runs the AI prediction, renders the draft board, and sends an embed to the "live-matches" channel tagging the player.
It also has a memory cache to avoid spamming the same match multiple times.
"""

import discord
from discord.ext import commands, tasks
import logging
from modules.interface.embed_formatter import build_predict_embed
from modules.interface.canvas_engine import render_draft_board
from modules.utils.parsers import extract_live_player_names

# Get the logger system
logger = logging.getLogger(__name__)

# This class handles the live tracker
class LiveTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracked_matches = set()  # Memory cache so it don't spam the same game twice
        self.match_check_loop.start()

    def cog_unload(self):
        self.match_check_loop.cancel()

    # Admin-only command to instantly configure the server
    @discord.app_commands.command(name="setup_broadcast", description="[ADMIN] Creates the #live-matches channel for automated predictions.")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def setup_broadcast(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command must be run in a server.", ephemeral=True)
            return

        # Prevent duplicate channels
        existing_channel = discord.utils.get(guild.channels, name="live-matches")
        if existing_channel:
            await interaction.response.send_message(
                f"⚠️ The broadcast channel already exists at {existing_channel.mention}!", ephemeral=True)
            return

        # Tell Discord to think
        await interaction.response.defer(ephemeral=True)

        try:
            new_channel = await guild.create_text_channel(
                name="live-matches",
                topic="🔴 Live Draft Predictions & Analytics from the Oratrice."
            )
            await interaction.followup.send(
                f"✅ Setup complete! Live matches will now automatically broadcast to {new_channel.mention}.")
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I do not have permission to create channels in this server. Please give me the 'Manage Channels' permission.")

    @tasks.loop(minutes=3.0)
    async def match_check_loop(self):
        await self.bot.wait_until_ready()

        # Looks for a channel exactly named "live-matches"
        channel = discord.utils.get(self.bot.get_all_channels(), name="live-matches")
        if not isinstance(channel, discord.TextChannel):
            return

        accounts = await self.bot.db.get_all_linked_accounts()
        if not accounts:
            return

        current_live_matches = set()

        for discord_id, puuid, riot_id, server in accounts:
            try:
                # Ping the Riot Spectator API using the specific player's server
                match_data = await self.bot.riot_client.get_live_match(puuid, platform_override=server)

                # Skip if not in game or API rate limit error
                if not isinstance(match_data, dict) or 'gameId' not in match_data:
                    continue

                match_id = match_data['gameId']
                current_live_matches.add(match_id)

                # Check if we already broadcasted this specific match
                if match_id in self.tracked_matches:
                    continue

                self.tracked_matches.add(match_id)
                logger.info(f"LIVE TRACKER: Detected {riot_id} entering match {match_id}. Broadcasting...")

                # Extract teams for the AI
                raw_blue_team = [p for p in match_data['participants'] if p['teamId'] == 100]
                raw_red_team = [p for p in match_data['participants'] if p['teamId'] == 200]

                blue_picks = [self.bot.champ_dict.get(str(p['championId']), 'Unknown') for p in raw_blue_team]
                red_picks = [self.bot.champ_dict.get(str(p['championId']), 'Unknown') for p in raw_red_team]

                # Run the AI Prediction
                final_blue_prob, final_red_prob, avg_blue_wr, avg_red_wr, blue_synergy, red_synergy = self.bot.ai_system.predict_live_match(
                    blue_picks, red_picks, self.bot.meta_db, self.bot.role_db
                )

                #  Extract Live Names
                positions = ['top', 'jungle', 'mid', 'adc', 'support']
                blue_names = dict(
                    zip(positions, extract_live_player_names(blue_picks, raw_blue_team, self.bot.champ_dict)))
                red_names = dict(
                    zip(positions, extract_live_player_names(red_picks, raw_red_team, self.bot.champ_dict)))

                #  Render the massive prediction canvas
                image_buffer = await render_draft_board(
                    blue_dict=dict(zip(positions, blue_picks)),
                    red_dict=dict(zip(positions, red_picks)),
                    role="None",
                    user_team="None",
                    banned_champs=None,
                    blue_names=blue_names,
                    red_names=red_names,
                    blue_prob=final_blue_prob,
                    red_prob=final_red_prob,
                    bg_filename="predict_bg.jpg"
                )

                file = discord.File(fp=image_buffer, filename="draft_board.png")
                embed = build_predict_embed(
                    final_blue_prob, final_red_prob, avg_blue_wr, avg_red_wr,
                    blue_synergy, red_synergy, match_data
                )

                # Ping the player in Discord!
                ping_string = f"🚨 **LIVE MATCH DETECTED!** <@{discord_id}> (`{riot_id}`) has entered the Rift!"

                await channel.send(content=ping_string, embed=embed, file=file)

            except Exception as e:
                logger.error(f"Live Tracker Error for {riot_id}: {e}")

        # Housekeeping: Remove old matches from memory so it doesn't inflate forever
        self.tracked_matches.intersection_update(current_live_matches)

async def setup(bot):
    await bot.add_cog(LiveTracker(bot))