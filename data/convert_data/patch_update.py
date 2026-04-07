import pandas as pd
from pandas import DataFrame
import subprocess
import sys
import os

"""
This script automates the entire "Rolling Window" update process.

BEFORE RUNNING:
1. Open `data_miner.py` and increase `TARGET_MATCHES` by 5,000 (e.g., 50000 -> 55000).
2. Save `data_miner.py`.
3. Run this script! It will handle the rest.
"""


def run_script(script_path):
    print(f"\n🚀 Starting: {script_path}...")
    try:
        # sys.executable ensures it uses the current Python virtual environment (.venv).
        subprocess.run([sys.executable, script_path], check=True)
        print(f"Finished: {script_path}!")
    except subprocess.CalledProcessError as e:
        print(f"\nError occurred while running {script_path}.")
        print(f"System details: {e}")
        print("Pipeline halted. Please fix the error above and try again.")
        sys.exit(1)


def prune_database():
    csv_path = "data/ranked_drafts.csv"
    print(f"\n Loading matches from {csv_path}...")

    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}!")
        sys.exit(1)

    df: DataFrame = pd.read_csv(csv_path)
    original_count = len(df)
    print(f"Current match count: {original_count}")

    # Keep only the 50,000 MOST RECENT games (drops the oldest ones at the top).
    df = df.tail(50000)

    df.to_csv(csv_path, index=False)
    print(f"✅ Successfully pruned {original_count - len(df)} old matches. CSV is back to 50k!")


if __name__ == "__main__":
    # The Safety Check.
    confirm = input("Did you increase TARGET_MATCHES by 5,000 in data_miner.py? (y/n): ")

    if confirm.lower() != 'y':
        print("🛑 Stopping. Please go update data_miner.py first!")
        sys.exit()

    # Run the Data Miner.
    run_script("data/convert_data/data_miner.py")

    # Prune the Old Data (The Rolling Window) Calling the function.
    prune_database()

    # Update the Math (Synergies & Meta).
    run_script("data/convert_data/build_synergy_matrix.py")
    run_script("data/convert_data/build_meta_db.py")

    #  Retrain the AI Brain.
    run_script("train_model.py")

    print("Pipeline Complete!")
    print("You can now safely restart your Discord bot.")