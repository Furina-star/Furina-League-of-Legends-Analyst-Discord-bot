"""
Dynamic Localization Engine
Automatically loads JSON files from data/locales/ into memory at startup.
"""

import discord
from discord import app_commands
from typing import Optional
import json
import os
import logging

# Get the logger system
logger = logging.getLogger(__name__)

# This class implements the app_commands.Translator interface to provide dynamic localization for Discord interactions.
class DiscordTranslator(app_commands.Translator):
    def __init__(self):
        self.translations = {}
        self._load_all_locales()

    # This method scans the data/locales/ directory for JSON files and loads them into memory.
    def _load_all_locales(self):
        # Resolve the absolute path to your data/locales folder
        base_dir = os.path.dirname(os.path.abspath(__file__))
        locales_dir = os.path.abspath(os.path.join(base_dir, "../../data/locales"))

        if not os.path.exists(locales_dir):
            logger.warning(f"Locales directory not found at {locales_dir}. Translations disabled.")
            return

        loaded_count = 0
        # Scan the directory for JSON files
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                # Extract the locale code (e.g., 'es-ES.json' -> 'es-ES')
                locale_code = filename[:-5]
                filepath = os.path.join(locales_dir, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.translations[locale_code] = json.load(f)
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to load translation file {filename}: {e}")

        logger.info(f"Translation Engine Online: Loaded {loaded_count} locale files.")

    # This method is called by the app_commands framework to get the translated string
    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext) -> Optional[str]:
        # locale.value returns the exact string matching our JSON filenames (e.g., 'es-ES')
        locale_str = locale.value

        # O(1) Memory Lookup
        if locale_str in self.translations:
            return self.translations[locale_str].get(string.message)

        # Fallback to default English if locale file doesn't exist
        return None