"""
This get all the items from the latest patch and creates a mapping of item ID to item name, which is used in the postgame review to show what items the player built.
"""

import urllib.request
import json
import os

def update_item_dictionary():
    print("Fetching the latest League of Legends patch version...")
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"

    with urllib.request.urlopen(version_url) as response:
        versions = json.loads(response.read().decode())
        latest_patch = versions[0]

    print(f"Latest patch is {latest_patch}. Downloading item data...")
    item_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_patch}/data/en_US/item.json"

    with urllib.request.urlopen(item_url) as response:
        item_data = json.loads(response.read().decode())

    clean_dict = {}
    for item_id, item_info in item_data['data'].items():
        clean_dict[item_id] = item_info['name']

    file_path = os.path.join(os.path.dirname(__file__), '..', 'Item_Dictionary.json')

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(clean_dict, f, indent=4)

    print(f"Successfully mapped {len(clean_dict)} items and saved to {file_path}!")

if __name__ == "__main__":
    update_item_dictionary()