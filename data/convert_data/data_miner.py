"""
data_miner.py
Spider Web Miner designed specifically for the 32-Feature ML Model.
Outputs directly to upgraded_drafts.csv.
"""
import asyncio
import csv
import os
import sys
import aiofiles
import pandas as pd
from collections import deque
from dotenv import load_dotenv
from riot_api import RiotAPIClient

load_dotenv()
RIOT_KEY = os.getenv('RIOT_API_KEY')
if not RIOT_KEY:
    sys.exit("Error: RIOT_API_KEY must be set in the .env file.")

REGION = "europe"
PLATFORM = "euw1"

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
CSV_FILENAME = str(os.path.join(SCRIPT_DIR, "..", "upgraded_drafts.csv"))

if os.path.exists(CSV_FILENAME):
    df = pd.read_csv(CSV_FILENAME, low_memory=False)
    assert isinstance(df, pd.DataFrame)
    current_rows = len(df)
    TARGET_MATCHES = current_rows + 50000
    print(f"Found {current_rows} matches. Auto-mining until {TARGET_MATCHES}...")
else:
    TARGET_MATCHES = 50000
    print("No database found. Starting fresh and mining matches...")


async def _load_existing_csv():
    visited_matches = set()
    matches_collected = 0

    if not os.path.exists(CSV_FILENAME):
        return visited_matches, matches_collected

    print("Found Existing CSV File! Loading Save State...")
    async with aiofiles.open(CSV_FILENAME, mode='r', newline='') as file:
        content = await file.read()
        reader = csv.reader(content.splitlines())
        next(reader, None)
        for row in reader:
            if row:
                visited_matches.add(row[0])
                matches_collected += 1

    print(f"Resuming from {matches_collected} matches...")
    return visited_matches, matches_collected


async def _create_csv_headers():
    async with aiofiles.open(CSV_FILENAME, mode='w', newline='') as file:
        headers = (
            "matchId,blueTop,blueJungle,blueMid,blueADC,blueSupport,"
            "redTop,redJungle,redMid,redADC,redSupport,blueWin,"
            "blueTopMastery,blueTopRank,blueJungleMastery,blueJungleRank,"
            "blueMidMastery,blueMidRank,blueADCMastery,blueADCRank,blueSupportMastery,blueSupportRank,"
            "redTopMastery,redTopRank,redJungleMastery,redJungleRank,"
            "redMidMastery,redMidRank,redADCMastery,redADCRank,redSupportMastery,redSupportRank\n"
        )
        await file.write(headers)


async def _rebuild_queue(client, seed_puuid):
    puuid_queue = deque([seed_puuid])
    seen_puuids = {seed_puuid}

    print("Save state detected. Force-fetching seed's latest match to rebuild the player queue...")

    seed_history = await client.get_match_history(seed_puuid, count=1)
    if seed_history:
        jumpstart_match = await client.get_match_details(seed_history[0])
        await asyncio.sleep(1.5)

        if jumpstart_match and 'info' in jumpstart_match:
            for p in jumpstart_match['info']['participants']:
                puuid = p['puuid']
                if puuid not in seen_puuids:
                    puuid_queue.append(puuid)
                    seen_puuids.add(puuid)

    print(f"Web Restored! Found {len(puuid_queue)} new players to branch out to.")
    return puuid_queue, seen_puuids


def _parse_draft(participants):
    draft = {"blue": {}, "red": {}}
    blue_win = 0

    for p in participants:
        team = "blue" if p['teamId'] == 100 else "red"
        role = p['teamPosition']

        if role not in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            return None, "invalid_role"

        draft[team][role] = {
            "championName": p['championName'],
            "championId": p['championId'],
            "puuid": p['puuid'],
            "summonerId": p.get('summonerId', '')
        }

        if team == "blue":
            blue_win = 1 if p['win'] else 0

    if len(draft["blue"]) == 5 and len(draft["red"]) == 5:
        return draft, blue_win

    return None, "incomplete_draft"


def _parse_rank_string(rank_str: str) -> float:
    # Defaults to Gold (3.0) exactly as configured in ai_wrapper.py
    if not rank_str or "Unranked" in rank_str:
        return 3.0

    upper_str = rank_str.upper()
    rank_map = {
        "IRON": 0.0, "BRONZE": 1.0, "SILVER": 2.0, "GOLD": 3.0,
        "PLATINUM": 4.0, "EMERALD": 5.0, "DIAMOND": 6.0,
        "MASTER": 7.0, "GRANDMASTER": 8.0, "CHALLENGER": 9.0
    }

    for tier, val in rank_map.items():
        if tier in upper_str:
            return val

    return 3.0


async def _fetch_player_stats(client, player_data):
    try:
        mastery = await client.get_champion_mastery(player_data['puuid'], player_data['championId'])
    except Exception:
        mastery = 0

    try:
        rank_str = await client.get_summoner_rank(player_data['puuid'])
        rank_val = _parse_rank_string(rank_str)
    except Exception:
        rank_val = 3.0

    return float(mastery), float(rank_val)


async def _append_row(match_id, draft, blue_win, stats):
    row = [
        match_id,
        draft["blue"]["TOP"]["championName"], draft["blue"]["JUNGLE"]["championName"],
        draft["blue"]["MIDDLE"]["championName"], draft["blue"]["BOTTOM"]["championName"],
        draft["blue"]["UTILITY"]["championName"],
        draft["red"]["TOP"]["championName"], draft["red"]["JUNGLE"]["championName"],
        draft["red"]["MIDDLE"]["championName"], draft["red"]["BOTTOM"]["championName"],
        draft["red"]["UTILITY"]["championName"],
        blue_win,
        stats["blue"]["TOP"]["mastery"], stats["blue"]["TOP"]["rank"],
        stats["blue"]["JUNGLE"]["mastery"], stats["blue"]["JUNGLE"]["rank"],
        stats["blue"]["MIDDLE"]["mastery"], stats["blue"]["MIDDLE"]["rank"],
        stats["blue"]["BOTTOM"]["mastery"], stats["blue"]["BOTTOM"]["rank"],
        stats["blue"]["UTILITY"]["mastery"], stats["blue"]["UTILITY"]["rank"],
        stats["red"]["TOP"]["mastery"], stats["red"]["TOP"]["rank"],
        stats["red"]["JUNGLE"]["mastery"], stats["red"]["JUNGLE"]["rank"],
        stats["red"]["MIDDLE"]["mastery"], stats["red"]["MIDDLE"]["rank"],
        stats["red"]["BOTTOM"]["mastery"], stats["red"]["BOTTOM"]["rank"],
        stats["red"]["UTILITY"]["mastery"], stats["red"]["UTILITY"]["rank"]
    ]
    async with aiofiles.open(CSV_FILENAME, mode='a', newline='') as file:
        await file.write(",".join(str(x) for x in row) + "\n")


async def _save_if_new(match_id, participants, visited_matches, matches_collected, client):
    visited_matches.add(match_id)
    parsed = _parse_draft(participants)
    if parsed[0] is None:
        return matches_collected

    draft, blue_win = parsed

    stats = {"blue": {}, "red": {}}
    tasks = []
    keys = []

    for team in ["blue", "red"]:
        for role in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            tasks.append(_fetch_player_stats(client, draft[team][role]))
            keys.append((team, role))

    # Gathers mastery and rank concurrently for maximum I/O speed.
    results = await asyncio.gather(*tasks)

    for (team, role), (mastery, rank) in zip(keys, results):
        stats[team][role] = {"mastery": mastery, "rank": rank}

    await _append_row(match_id, draft, blue_win, stats)
    matches_collected += 1
    print(f"✅ Saved Match {matches_collected}/{TARGET_MATCHES} [{match_id}]")
    return matches_collected


async def _process_match_history(client, match_history, visited_matches, puuid_queue, seen_puuids, matches_collected):
    for match_id in match_history:
        if matches_collected >= TARGET_MATCHES:
            break

        if match_id in visited_matches:
            continue

        match_data = await client.get_match_details(match_id)
        await asyncio.sleep(1.5)

        if not match_data or 'info' not in match_data:
            continue

        participants = match_data['info']['participants']

        for p in participants:
            puuid = p['puuid']
            if puuid not in seen_puuids:
                puuid_queue.append(puuid)
                seen_puuids.add(puuid)

        matches_collected = await _save_if_new(match_id, participants, visited_matches, matches_collected, client)

    return matches_collected


async def mine_data(seed_game_name, seed_tag_line):
    client = RiotAPIClient(api_key=RIOT_KEY, default_platform=PLATFORM, default_region=REGION)
    await client.setup_cache()

    os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
    visited_matches, matches_collected = await _load_existing_csv()

    if not os.path.exists(CSV_FILENAME):
        await _create_csv_headers()

    if matches_collected >= TARGET_MATCHES:
        print("🎯 Target already reached! No mining needed.")
        await client.close()
        return

    print(f"🌱 Planting seed: {seed_game_name}#{seed_tag_line}")
    seed_puuid = await client.get_puuid(seed_game_name, seed_tag_line)
    if not seed_puuid:
        print("❌ Invalid Seed Player.")
        await client.close()
        return

    if matches_collected > 0:
        puuid_queue, seen_puuids = await _rebuild_queue(client, seed_puuid)
    else:
        puuid_queue = deque([seed_puuid])
        seen_puuids = {seed_puuid}

    stop_event = asyncio.Event()

    async def spider_loop():
        nonlocal matches_collected
        while puuid_queue and not stop_event.is_set():
            current_puuid = puuid_queue.popleft()
            print(f"\n🔍 Scanning new player... (Queue size: {len(puuid_queue)})")

            match_history = await client.get_match_history(current_puuid, count=20)
            if not match_history:
                continue

            matches_collected = await _process_match_history(
                client, match_history, visited_matches, puuid_queue, seen_puuids, matches_collected
            )

            if matches_collected >= TARGET_MATCHES:
                stop_event.set()

        print("\n🎉 DATA MINING COMPLETE!")

    await spider_loop()
    await client.close()


if __name__ == "__main__":
    asyncio.run(mine_data("Agurin", "DND"))