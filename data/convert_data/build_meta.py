import pandas as pd
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR) # Adjust if your csv is in a different spot
CSV_PATH = os.path.join(DATA_DIR, "ranked_drafts.csv")
JSON_PATH = os.path.join(DATA_DIR, "Meta_Champions.json")

def build_meta_database():
    print(f"Reading match data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)

    # Dictionary to hold our raw stats: {"Volibear": {"wins": 0, "games": 0}}
    meta_stats = {}

    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    print(f"Calculating Global Win Rates across {len(df)} matches...")

    for index, row in df.iterrows():
        blue_won = row['blueWin'] == 1

        # Tally Blue Team
        for col in blue_cols:
            champ = str(row[col])
            if champ not in meta_stats:
                meta_stats[champ] = {"wins": 0, "games": 0}
            meta_stats[champ]["games"] += 1
            if blue_won:
                meta_stats[champ]["wins"] += 1

        # Tally Red Team
        for col in red_cols:
            champ = str(row[col])
            if champ not in meta_stats:
                meta_stats[champ] = {"wins": 0, "games": 0}
            meta_stats[champ]["games"] += 1
            if not blue_won:
                meta_stats[champ]["wins"] += 1

    # Calculate the final percentages
    final_meta = {}
    for champ, stats in meta_stats.items():
        # Only log them if they've been played at least 50 times to avoid 100% WR anomalies
        if stats["games"] >= 50:
            win_rate = stats["wins"] / stats["games"]
            final_meta[champ] = round(win_rate, 4)
        else:
            # If a champion is practically never played, default them to exactly 50%
            final_meta[champ] = 0.5000

    # Save the brain
    with open(JSON_PATH, "w") as f:
        json.dump(final_meta, f, indent=4)

    print(f"✅ Meta Database built successfully! Tracked {len(final_meta)} champions.")

if __name__ == "__main__":
    build_meta_database()