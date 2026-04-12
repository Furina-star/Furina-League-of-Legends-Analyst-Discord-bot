"""
This is where data are load properly and stored in global variables for use across the bot.
It handles loading item and rune data from JSON files, and provides reverse lookups for item names to IDs.
It also includes error handling for missing or corrupted data files, with appropriate logging warnings.
"""

import json
import logging
import os
import requests
from config import (
    KEYSTONE_RUNES_PATH, ITEM_DICT_PATH, SUMMONER_SPELLS,
    META_PATH, ROLES_PATH, CHAMP_DICT_PATH
)

# Get the logging system
logger = logging.getLogger(__name__)

# JSON Loader
def _load_json(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data:
                logger.warning(f"WARNING: {path} exists but is empty!")
            return data
    except FileNotFoundError:
        logger.warning(f"WARNING: {path} not found! Run the build scripts in data/convert_data/ first.")
        return {}
    except json.JSONDecodeError:
        logger.warning(f"WARNING: {path} is corrupted!")
        return {}

ITEM_DB = _load_json(ITEM_DICT_PATH)
RUNE_DB = _load_json(KEYSTONE_RUNES_PATH)
SPELL_DB = SUMMONER_SPELLS
META_DB = _load_json(META_PATH)
ROLE_DB = _load_json(ROLES_PATH)

# Reverse lookup: "Zhonya's Hourglass" -> 3157
# Filter to base item IDs only (4 digits, no Ornn upgrade prefixes)
ITEM_NAME_TO_ID = {
    name: int(item_id)
    for item_id, name in ITEM_DB.items()
    if len(item_id) == 4
}

# Champion Mapping
_CACHE_FILE = CHAMP_DICT_PATH
def load_champion_mapping() -> tuple[str, dict]:
    try:
        # Fetch just the version number
        latest_version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10).json()[0]

        # Check if cache exists and is up to date
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE) as f:
                cached = json.load(f)
                if cached.get("version") == latest_version:
                    return cached["version"], cached["mapping"]

        # If no cache exists, or the patch updated, download the heavy file
        champ_data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json",timeout=10).json()
        id_to_name = {str(info['key']): name for name, info in champ_data['data'].items()}
        id_to_name["-1"] = "None"

        # Save the new mapping and version to the cache file
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, "w") as f:
            json.dump({"version": latest_version, "mapping": id_to_name}, f, indent=4)

        return latest_version, id_to_name

    except Exception as e:
        logger.error(f"Data Dragon error: {e}")

        # Just in case the Riot Server is down (Imagine RITO????)
        if os.path.exists(_CACHE_FILE):
            logger.warning("Network failed: falling back to local cache.")
            with open(_CACHE_FILE) as f:
                data = json.load(f)
                return data.get("version", "15.1.1"), data.get("mapping", {})

        return "15.1.1", {} # Return an empty dictionary if everything fails