"""
This handle embed formatting for the commands.
It takes in the relevant data and constructs a Discord Embed object with the appropriate structure and styling for each command's output.
"""

import discord
from typing import List

# For help commands in cogs
def build_help_embed() -> discord.Embed:
    
    embed = discord.Embed(
        title="💧 Furina League Analyst Bot - Help Menu",
        description="I am Furina, your personal Solo Queue analyst! Here is how to use my commands:\n"
                    "Prefix: `f` or `furina` (e.g., `f ping`, `f predict`)",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🏓 `f ping`",
        value="Checks if Furina is online.",
        inline=False
    )
    embed.add_field(
        name="⚔️ `f predict`",
        value="Calculates win probability for a live match.\n"
              "**Format:** `f predict <server> Name#Tag`\n"
              "**Example:** `f predict KR Hide on bush#KR1`",
        inline=False
    )
    embed.add_field(
        name="🕵️ `f scout`",
        value="Builds an enemy dossier for a live match.\n"
              "**Format:** `f scout <server> Name#Tag`\n"
              "**Example:** `f scout NA1 Doublelift#NA1`",
        inline=False
    )
    embed.set_footer(
        text="Valid servers: NA1, EUW1, EUN1, KR, SG2, TW2, VN2, TH2, PH2, BR1, LAN1, LAS1, OC1, TR1, RU"
    )

    return embed

# For predict commands in cogs
def build_predict_embed(blue_prob: float, red_prob: float,
                        avg_blue_wr: float, avg_red_wr: float,
                        blue_synergy: float, red_synergy: float,
                        blue_display: List[str], red_display: List[str]) -> discord.Embed:
    embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", color=discord.Color.blue())

    blue_text = (
            f"**Win Chance: {blue_prob * 100:.1f}%**\n"
            f"*(Avg WR: {avg_blue_wr:.1f}%)*\n"
            f"*(Synergy: {blue_synergy * 100:+.1f})*\n\n"
            f"**Draft:**\n" + "\n".join(blue_display)
    )

    red_text = (
            f"**Win Chance: {red_prob * 100:.1f}%**\n"
            f"*(Avg WR: {avg_red_wr:.1f}%)*\n"
            f"*(Synergy: {red_synergy * 100:+.1f})*\n\n"
            f"**Draft:**\n" + "\n".join(red_display)
    )

    embed.add_field(name="🟦 Blue Team", value=blue_text, inline=True)
    embed.add_field(name="🟥 Red Team", value=red_text, inline=True)

    return embed

# All what ifs to be used for build_scout_embed
def _generate_player_tags(rank: str, mastery: int, is_duo: bool) -> str:
    tags = []

    # Duo Detection Tag!
    if is_duo:
        tags.append("❤ **DUO**")

    # OTP and First Timer tag
    if mastery >= 1000000:
        tags.append("⚠️ **OTP WARNING**")
    elif mastery >= 500000:
        tags.append("🔸 **Main**")
    elif mastery < 10000:
        tags.append("🔰 **First Time / Very New**")

    # Smurf Detection Tag
    if any(win_rate in rank for win_rate in ["70.", "75.", "80.", "85.", "90."]) and "Unranked" not in rank:
        tags.append("🕵️ **SUSPECTED SMURF**")

    if tags:
        return f"\n**Tags:** {' | '.join(tags)}"
    return ""

# For scout command in cogs
def build_scout_embed(server: str, game_name: str, bots: List[str], players: List[tuple]) -> discord.Embed:
    embed = discord.Embed(
        title=f"🕵️ Enemy Team Dossier ({server.upper()})",
        description=f"Scouting for **{game_name}**",
        color=discord.Color.dark_purple()
    )

    for c_name in bots:
        embed.add_field(name=f"🤖 {c_name} (Bot)", value="No data available.", inline=False)

    for c_name, riot_id, rank, mastery, is_duo in players:
        tag_string = _generate_player_tags(rank, mastery, is_duo)

        embed.add_field(
            name=f"⚔️ {c_name} - {riot_id}",
            value=f"**Rank:** {rank}\n**Mastery:** {mastery:,} pts{tag_string}",
            inline=False
        )

    return embed
