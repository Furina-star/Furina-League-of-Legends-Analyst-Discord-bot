"""
This is the parsers module, which contains all the helper functions for parsing and processing data related to League of Legends.
This includes functions for parsing Riot IDs, extracting win rates from rank strings, sorting team compositions by role, and detecting autofill situations by comparing a player's primary role from match history against their current inferred position.
These functions are designed to be reusable across different parts of the bot, ensuring consistent data handling and improving code maintainability.
"""

import re
import logging

# Get the logging system
logger = logging.getLogger(__name__)

# Initiate Riot ID Parser as a function.
# Helper number two for Duo detection
def find_duos(player_histories: list) -> set:
    duos = set()
    # Compare every player's match history against every other player's history
    for i in range(len(player_histories)):
        for j in range(i + 1, len(player_histories)):
            p1_id, p1_matches = player_histories[i]
            p2_id, p2_matches = player_histories[j]

            # If the lists intersect (share a Match ID), they're playing together lol
            if p1_matches and p2_matches:
                shared_games = set(p1_matches).intersection(p2_matches)

                if len(shared_games) >= 2:  # If they have 2 or more shared games in their recent history, they're probably duos
                    duos.add(p1_id)
                    duos.add(p2_id)
    return duos

# this is to prevent the user from formatting it wrong, for example they might type "Hide on bush KR1" instead of "Hide on bush#KR1".
def parse_riot_id(full_riot_id: str):
    if len(full_riot_id) > 22:  # 16 (name) + 1 (#) + 5 (tag)
        return None, None

    if '#' in full_riot_id:
        game_name, tag_line = full_riot_id.split('#', 1)
    else:
        parts = full_riot_id.rsplit(' ', 1)
        if len(parts) == 2:
            game_name, tag_line = parts[0], parts[1]
        else:
            return None, None  # Returns None if they formatted it completely wrong

    return game_name.strip(), tag_line.strip()

# Initiate Winrate as a function
def parse_winrate(rank_string):
    if not rank_string or "Unranked" in rank_string:
        return 50.0  # If unranked or missing, assume an average 50% player

    # Searches for numbers directly followed by "% WR"
    match = re.search(r"([\d.]+)%\sWR", rank_string)
    if match:
        return float(match.group(1))
    return 50.0

# Initiate Role Sorter as a function.
def _assign_role_from_pool(roles, unassigned, role_idx, db_key, meta_db):
    if roles[role_idx] is not None:
        return
    pool = meta_db.get(db_key, set())
    for i, champ in enumerate(unassigned):
        if champ in pool:
            roles[role_idx] = champ
            unassigned.pop(i)
            return

# Sort Team Composition by role, not by pick
def sort_team_roles(team_participants, champ_dict, meta_db):
    roles = [None] * 5
    unassigned = []

    for player in team_participants:
        champ_name = champ_dict.get(str(player['championId']), "Unknown")
        if roles[1] is None and 11 in (player.get('spell1Id'), player.get('spell2Id')):
            roles[1] = champ_name
        else:
            unassigned.append(champ_name)

    # Use the new external helper instead of a nested function
    _assign_role_from_pool(roles, unassigned, 3, "PURE_ADCS", meta_db)
    _assign_role_from_pool(roles, unassigned, 4, "PURE_SUPPORTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 3, "FLEX_BOTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 4, "FLEX_SUPPORTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 2, "KNOWN_MIDS", meta_db)
    _assign_role_from_pool(roles, unassigned, 0, "KNOWN_TOPS", meta_db)

    for i in range(5):
        if roles[i] is None and unassigned:
            roles[i] = unassigned.pop(0)

    if None in roles or unassigned:
        return [champ_dict.get(str(p['championId']), "Unknown") for p in team_participants]

    return roles

# Detect's if the enemy is Autofilled
def detect_autofill(primary_role: str, current_position: str) -> bool:
    if not primary_role or not current_position:
        return False

    return primary_role != current_position

# Initiate the ban logic as a function
def extract_bans(match_data: dict, champ_dict: dict):
    blue_bans, red_bans = ["None"] * 5, ["None"] * 5
    b_count, r_count = 0, 0
    for ban in match_data.get('bannedChampions', []):
        c_name = champ_dict.get(str(ban['championId']), "None")
        if ban['teamId'] == 100 and b_count < 5:
            blue_bans[b_count] = c_name
            b_count += 1
        elif ban['teamId'] == 200 and r_count < 5:
            red_bans[r_count] = c_name
            r_count += 1
    return blue_bans, red_bans

# Initiate the checking logic as a function
def check_if_bot(champ_name: str, raw_team: list, champ_dict: dict):
    for p in raw_team:
        if champ_dict.get(str(p['championId']), "Unknown") == champ_name:
            return p.get('bot', False) or not p.get('puuid')
    return False

# Formats the team display strings.
def format_team_display(team_picks: list, raw_team: list, meta_db: dict, champ_dict: dict):
    display = []
    for c in team_picks:
        meta_wr = meta_db.get(c, 0.5000) * 100
        # Pass the champ_dict into the bot checker!
        bot_tag = "🤖 " if check_if_bot(c, raw_team, champ_dict) else ""
        display.append(f"{bot_tag}{c} `[{meta_wr:.1f}%]`")
    return display
