"""
This is the live tracker where it auto-detects when a linked player enters a live match and broadcasts it in a specific channel with the prediction and draft board.
It runs every 3 minutes and checks all linked accounts against the Riot Spectator API.
If it finds a new live match, it extracts the teams, runs the AI prediction, renders the draft board, and sends an embed to the "live-matches" channel tagging the player.
It also has a memory cache to avoid spamming the same match multiple times.
"""

import discord
from discord.ext import commands, tasks
import logging
import asyncio
import json
from config import RANK_WEIGHTS
from modules.interface.embed_formatter import build_predict_embed
from modules.interface.canvas_engine import render_draft_board
from modules.utils.parsers import extract_live_player_names

# Get the logger system
logger = logging.getLogger(__name__)

class LiveTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracked_matches = set()
        self.rank_cache = {}
        self.match_check_loop.start()
        self.passive_miner_loop.start()

    def cog_unload(self):
        self.match_check_loop.cancel()
        self.passive_miner_loop.cancel()

    # Admin-only command to instantly configure the server
    @discord.app_commands.command(name="setup_broadcast", description="[ADMIN] Creates the #live-matches channel for automated predictions.")
    @discord.app_commands.checks.has_permissions(manage_channels=True)
    async def setup_broadcast(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command must be run in a server.", ephemeral=True)
            return

        existing_channel = discord.utils.get(guild.channels, name="live-matches")
        if existing_channel:
            await interaction.response.send_message(
                f"⚠️ The broadcast channel already exists at {existing_channel.mention}!", ephemeral=True)
            return

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

        channel = discord.utils.get(self.bot.get_all_channels(), name="live-matches")
        if not isinstance(channel, discord.TextChannel):
            return

        accounts = await self.bot.db.get_all_linked_accounts()
        if not accounts:
            return

        current_live_matches = set()

        for discord_id, puuid, riot_id, server in accounts:
            try:
                match_data = await self.bot.riot_client.get_live_match(puuid, platform_override=server)

                if not isinstance(match_data, dict) or 'gameId' not in match_data:
                    continue

                match_id = match_data['gameId']
                current_live_matches.add(match_id)

                if match_id in self.tracked_matches:
                    continue

                self.tracked_matches.add(match_id)
                logger.info(f"LIVE TRACKER: Detected {riot_id} entering match {match_id}. Broadcasting...")

                raw_blue_team = [p for p in match_data['participants'] if p['teamId'] == 100]
                raw_red_team = [p for p in match_data['participants'] if p['teamId'] == 200]

                blue_picks = [self.bot.champ_dict.get(str(p['championId']), 'Unknown') for p in raw_blue_team]
                red_picks = [self.bot.champ_dict.get(str(p['championId']), 'Unknown') for p in raw_red_team]

                final_blue_prob, final_red_prob, avg_blue_wr, avg_red_wr, blue_synergy, red_synergy = self.bot.ai_system.predict_live_match(
                    blue_picks, red_picks, self.bot.meta_db, self.bot.role_db
                )

                positions = ['top', 'jungle', 'mid', 'adc', 'support']
                blue_names = dict(zip(positions, extract_live_player_names(blue_picks, raw_blue_team, self.bot.champ_dict)))
                red_names = dict(zip(positions, extract_live_player_names(red_picks, raw_red_team, self.bot.champ_dict)))

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

                ping_string = f"🚨 **LIVE MATCH DETECTED!** <@{discord_id}> (`{riot_id}`) has entered the Rift!"
                await channel.send(content=ping_string, embed=embed, file=file)

            except Exception as e:
                logger.error(f"Live Tracker Error for {riot_id}: {e}")

        # Housekeeping: Remove old matches from memory
        self.tracked_matches.intersection_update(current_live_matches)

    # Helper function for the passive miner loop
    async def _fetch_player_stats(self, p, server):
        puuid = p['puuid']
        champ_id = p['championId']

        # Fetch Mastery
        mastery = await self.bot.riot_client.get_champion_mastery(puuid, champ_id, platform_override=server)

        # Fetch Rank using bounded class-level memory cache
        if puuid in self.rank_cache:
            rank_val = self.rank_cache[puuid]
        else:
            rank_str = await self.bot.riot_client.get_summoner_rank(puuid, platform_override=server)
            # Use the imported RANK_WEIGHTS
            rank_val = RANK_WEIGHTS.get(rank_str.upper().split()[0], 3) if rank_str else 3

            # Prevent infinite memory leakage
            if len(self.rank_cache) > 5000:
                self.rank_cache.clear()
            self.rank_cache[puuid] = rank_val

        return champ_id, mastery, rank_val

    @tasks.loop(seconds=25)
    async def passive_miner_loop(self):
        await self.bot.wait_until_ready()

        pending_match = await self.bot.db.get_one_queued_match()
        if not pending_match:
            return

        match_id, server = pending_match

        try:
            match_data = await self.bot.riot_client.get_match_details(match_id, server_context=server)
            participants = match_data.get('info', {}).get('participants', [])

            if len(participants) != 10:
                await self.bot.db.remove_from_queue(match_id)
                return

            blue_win = 1 if participants[0].get('win', False) else 0
            payload = {}
            roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']

            # High Optimization: Fetch all 10 players simultaneously using asyncio.gather
            fetch_tasks = [self._fetch_player_stats(p, server) for p in participants]
            results = await asyncio.gather(*fetch_tasks)

            # Reconstruct the payload
            for i, (champ_id, mastery, rank_val) in enumerate(results):
                team_prefix = 'blue' if i < 5 else 'red'
                role = roles[i % 5]

                payload[f'{team_prefix}{role}'] = champ_id
                payload[f'{team_prefix}{role}Mastery'] = mastery
                payload[f'{team_prefix}{role}Rank'] = rank_val

            # Save finalized AI data and pop from queue
            await self.bot.db.save_ml_data(match_id, blue_win, json.dumps(payload))
            await self.bot.db.remove_from_queue(match_id)

        except Exception as e:
            if "429" not in str(e):
                await self.bot.db.remove_from_queue(match_id)

async def setup(bot):
    await bot.add_cog(LiveTracker(bot))