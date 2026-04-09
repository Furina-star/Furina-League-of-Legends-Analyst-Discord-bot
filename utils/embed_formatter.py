"""
This handle embed formatting for the commands.
It takes in the relevant data and constructs a Discord Embed object with the appropriate structure and styling for each command's output.
"""

import discord
import re
from typing import List, Tuple

# For help commands in cogs
def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💧 Furina League Analyst Bot - Help Menu",
        description="I am Furina, your personal Solo Queue analyst! I now use **Slash Commands**:\n"
                    "Just type `/` and select my commands from the menu!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🏓 `/ping`",
        value="Checks my current latency to Discord.",
        inline=False
    )
    embed.add_field(
        name="⚔️ `/predict`",
        value="Calculates win probability for a live match.\n"
              "**Requires:** Server and Riot ID",
        inline=False
    )
    embed.add_field(
        name="🕵️ `/scout`",
        value="Builds an enemy dossier for a live match.\n"
              "**Requires:** Server and Riot ID",
        inline=False
    )
    embed.set_footer(
        text="Valid servers: NA1, EUW1, EUN1, KR, SG2, TW2, VN2, TH2, PH2, BR1, LAN1, LAS1, OC1, TR1, RU"
    )

    return embed

# For predict commands in cogs
def build_predict_embeds(blue_prob: float, red_prob: float,
                         avg_blue_wr: float, avg_red_wr: float,
                         blue_synergy: float, red_synergy: float,
                         blue_display: List[str], red_display: List[str]) -> Tuple[discord.Embed, discord.Embed]:

    description = f"**Blue Win Chance:** {blue_prob * 100:.1f}%\n**Red Win Chance:** {red_prob * 100:.1f}%"

    # Blue
    blue_embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", description=description, color=discord.Color.blue())
    blue_text = (
            f"*(Avg WR: {avg_blue_wr:.1f}%)*\n"
            f"*(Synergy: {blue_synergy * 100:+.1f})*\n\n"
            f"**Draft:**\n" + "\n".join(blue_display)
    )
    blue_embed.add_field(name="🟦 Blue Team Data", value=blue_text, inline=False)

    # Red
    red_embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", description=description, color=discord.Color.red())
    red_text = (
            f"*(Avg WR: {avg_red_wr:.1f}%)*\n"
            f"*(Synergy: {red_synergy * 100:+.1f})*\n\n"
            f"**Draft:**\n" + "\n".join(red_display)
    )
    red_embed.add_field(name="🟥 Red Team Data", value=red_text, inline=False)

    return blue_embed, red_embed

# Helper functions for _generate_player_tags
# OTP and First timer detection
def _get_mastery_tags(mastery: int, is_otp: bool = False) -> list:
    if mastery >= 1000000:
        return [] if is_otp else ["🦄 **OTP WARNING**"]
    if mastery >= 500000:
        return ["🛡️ **Main**"]
    if mastery < 10000:
        return ["🔰 **First Time / Very New**"]
    return []

# Meta slave and Troll detection
def _get_meta_tags(meta_wr: float) -> list:
    if meta_wr >= 0.525:
        return ["🎯 **Meta Abuser**"]
    if meta_wr <= 0.48:
        return ["🤡 **Off-Meta / Troll**"]
    return []


# Winrate detection
def _get_winrate_tags(rank: str) -> list:
    tags = []

    # Smurf Detection
    if re.search(r"\b([789]\d)\.\d+%\s*WR", rank) and "Unranked" not in rank:
        tags.append("🕵️ **SUSPECTED SMURF**")

    # Tactical Winrate Analysis
    match = re.search(r"([\d.]+)%\sWR\*\*\s\((\d+)\sgames\)", rank)
    if match:
        wr = float(match.group(1))
        games = int(match.group(2))

        if wr >= 60.0 and games >= 40:
            tags.append("🔥 **1v9 Machine**")
        elif wr <= 45.0 and games >= 30:
            tags.append("🥶 **Tilted**")

        if games >= 500 and 49.0 <= wr <= 51.0:
            tags.append("🧱 **Hardstuck**")

    return tags

# All what ifs to be used for build_scout_embed
def _generate_player_tags(rank: str, mastery: int, is_duo: bool, meta_wr: float, is_otp=False, is_autofilled=False) -> str:
    tags = []

    if is_duo: tags.append("❤ **DUO**")
    if is_otp: tags.append("👑 **TRUE OTP**")
    if is_autofilled: tags.append("⚠️ **AUTOFILLED**")

    # Append all the helper functions above
    tags.extend(_get_meta_tags(meta_wr))
    tags.extend(_get_winrate_tags(rank))
    tags.extend(_get_mastery_tags(mastery, is_otp))

    # Join all tags into a single string, separated by " | ", and return it. If no tags, return an empty string.
    if tags:
        return f"\n**Tags:** {' | '.join(tags)}"
    return ""

# For scout command in cogs
def build_scout_embed(server: str, game_name: str, bots: list, players: list, meta_db: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"🕵️ Enemy Team Dossier ({server.upper()})",
        description=f"Scouting for **{game_name}**",
        color=discord.Color.dark_purple()
    )

    for c_name in bots:
        embed.add_field(name=f"🤖 {c_name} (Bot)", value="No data available.", inline=False)

    for c_name, riot_id, rank, mastery, is_duo, keystone, is_otp, is_autofilled in players:
        meta_wr = meta_db.get(c_name, 0.50)
        tag_string = _generate_player_tags(rank, mastery, is_duo, meta_wr, is_otp, is_autofilled)

        keystone_display = f" [{keystone}]" if keystone != "None" else ""

        embed.add_field(
            name=f"⚔️ {c_name}{keystone_display} - {riot_id}",
            value=f"**Rank:** {rank}\n**Mastery:** {mastery:,} pts{tag_string}",
            inline=False
        )

    return embed
