"""
This is a script that get all the Keystone Runes.
"""

import urllib.request
import json
import os

def update_rune_dictionary():
    print("Fetching the latest League of Legends patch version...")
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"

    with urllib.request.urlopen(version_url) as response:
        versions = json.loads(response.read().decode())
        latest_patch = versions[0]

    print(f"Latest patch is {latest_patch}. Downloading Rune data...")
    rune_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_patch}/data/en_US/runesReforged.json"

    with urllib.request.urlopen(rune_url) as response:
        rune_data = json.loads(response.read().decode())

    clean_dict = {}

    # Riot's rune data is nested deeply (Tree -> Slots -> Runes)
    # This loop digs all the way down to extract every single rune ID and Name!
    for tree in rune_data:
        for slot in tree['slots']:
            for rune in slot['runes']:
                clean_dict[str(rune['id'])] = rune['name']

    # Save it directly into your /data/ directory
    file_path = os.path.join(os.path.dirname(__file__), '..', 'Keystone_Runes.json')

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(clean_dict, f, indent=4)

    print(f"Successfully mapped {len(clean_dict)} runes and saved to {file_path}!")


if __name__ == "__main__":
    update_rune_dictionary()