"""
This is where data are load properly and stored in global variables for use across the bot.
It handles loading item and rune data from JSON files, and provides reverse lookups for item names to IDs.
It also includes error handling for missing or corrupted data files, with appropriate logging warnings.
"""

import json
import logging
from config import KEYSTONE_RUNES_PATH, ITEM_DICT_PATH, SUMMONER_SPELLS


logger = logging.getLogger(__name__)

def _load_json(path):
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

# Reverse lookup: "Zhonya's Hourglass" -> 3157
# Filter to base item IDs only (4 digits, no Ornn upgrade prefixes)
ITEM_NAME_TO_ID = {
    name: int(item_id)
    for item_id, name in ITEM_DB.items()
    if len(item_id) == 4
}