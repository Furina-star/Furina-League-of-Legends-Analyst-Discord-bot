"""
This script automates the entire AI Evolution process.
Run this once a week to absorb all passively mined data, update the meta JSONs, and retrain the PyTorch model.
"""

import subprocess
import sys
import os

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = str(os.path.dirname(SCRIPT_DIR))
ROOT_DIR = os.path.dirname(DATA_DIR)

def run_script(script_name, cwd=SCRIPT_DIR):
    script_path = str(os.path.join(cwd, script_name))
    print(f"\n🚀 Starting: {script_name}...")
    try:
        subprocess.run([sys.executable, script_path], check=True, cwd=ROOT_DIR)
        print(f"✅ Finished: {script_name}!")
    except subprocess.CalledProcessError:
        print(f"\n❌ Error occurred while running {script_name}.")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting Autonomous AI Evolution Pipeline...")

    # Rebuild Heuristics from the hybrid data
    run_script("build_synergy_matrix.py")
    run_script("build_meta.py")
    run_script("update_roles.py")

    # Static data updates from Riot
    run_script("build_items.py")
    run_script("build_runes.py")

    # Retrain the Deep Learning Model
    print("\n🧠 Initiating Deep Learning Retraining...")
    # Point execution to the root directory for train_model.py
    run_script("train_model.py", cwd=ROOT_DIR)

    print("\n🏆 Pipeline Complete! The AI is fully updated and ready for Discord.")