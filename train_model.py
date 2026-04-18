"""
This is where to train the model for league of legends analysis.
"""
import joblib
import pandas as pd
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import requests
import json
import os
import logging
import config
import sqlite3
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader
from safetensors.torch import save_file, load_file
from services.ai_wrapper import calculate_team_synergy, Model

# Get the logging system
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Device setup for GPU Acceleration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Training on hardware device: {device}")

# Load the mined Data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
logger.info("Loading MVP Dataset...")
df_csv = pd.read_csv("data/training/upgraded_drafts.csv")

# Extract passively mined data from the SQLite Database
logger.info("Extracting Live Mined Data from Database...")
db_data = []
with sqlite3.connect("data/live/server_state.db") as conn:
    cursor = conn.cursor()
    # Fetch all passively mined matches
    cursor.execute("SELECT match_id, blue_win, payload FROM ml_training_data")
    rows = cursor.fetchall()

    for match_id, blue_win, payload_str in rows:
        payload = json.loads(payload_str)
        payload['matchId'] = match_id
        payload['blueWin'] = blue_win
        db_data.append(payload)

# Merge them together in memory
if db_data:
    df_db = pd.DataFrame(db_data)
    df = pd.concat([df_csv, df_db], ignore_index=True)
    logger.info(f"Merged {len(df_csv)} CSV matches with {len(df_db)} Database matches (Total: {len(df)}).")
else:
    df = df_csv

# Load the Synergy Matrix
logger.info("Loading Synergy Matrix...")
with open("data/static/Synergy_Matrix.json", "r") as f:
    synergy_matrix = json.load(f)

# Load the Meta Champions
logger.info("Loading Meta Database...")
with open("data/static/Meta_Champions.json", "r") as f:
    meta_db = json.load(f)

# Calculate Synergy Scores for every match using Pandas (Super Fast!)
logger.info("Calculating Team Synergy Scores...")
blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']
all_cols = blue_cols + red_cols

# This applies your calculator function to every single row in the CSV and creates two new columns
df['blueSynergy'] = df.apply(lambda row: calculate_team_synergy([str(row[c]) for c in blue_cols], synergy_matrix, 0.50), axis=1)
df['redSynergy'] = df.apply(lambda row: calculate_team_synergy([str(row[c]) for c in red_cols], synergy_matrix, 0.50), axis=1)

# Create a quick helper function to grab the 10 win rates for every row in the CSV
def get_meta_rates(row):
    return [meta_db.get(str(row[c]), 0.5000) for c in all_cols]
df['metaRates'] = df.apply(get_meta_rates, axis=1)

# Grabbing every single champion out there just to be safe
logger.info("Downloading Master Champion List From Riot...")
version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
champ_data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json").json()

all_champions = []
for champ_id, info in champ_data['data'].items():
    all_champions.append(champ_id)
    all_champions.append(info['name'])

all_champions.extend(['None', 'Unknown'])

# Encode
le = LabelEncoder()
le.fit(all_champions)
text_cols = [col for col in df.columns if col not in ['blueWin', 'matchId', 'blueSynergy', 'redSynergy', 'metaRates']]

logger.info("Translating CSV data...")
for col in text_cols:
    df[col] = df[col].apply(lambda x: x if x in le.classes_ else 'Unknown')
    df[col] = le.transform(df[col].astype(str))

# Save LabelEncoder using skops
champion_mapping = {str(champ): int(idx) for idx, champ in enumerate(le.classes_)}
with open("data/models/champion_encoder.json", "w") as f:
    json.dump(champion_mapping, f, indent=4)

num_unique_champions = len(le.classes_)

# Calculate meta columns
logger.info("Calculating Meta Scores...")
roles_map = [('Top', 'top'), ('Jungle', 'jungle'), ('Mid', 'mid'), ('ADC', 'adc'), ('Support', 'support')]

for role_cap, role_low in roles_map:
    # Safely get the meta score, using r=role_low to force early binding of the loop variable
    df[f'blue{role_cap}Meta'] = df[f'blue{role_cap}'].apply(lambda c, r=role_low: meta_db.get(str(c), {}).get(r, 0.5))
    df[f'red{role_cap}Meta'] = df[f'red{role_cap}'].apply(lambda c, r=role_low: meta_db.get(str(c), {}).get(r, 0.5))

logger.info("Extracting and Scaling Player Masteries and Ranks...")

roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']
mastery_cols = [f'blue{role}Mastery' for role in roles] + [f'red{role}Mastery' for role in roles]
rank_cols = [f'blue{role}Rank' for role in roles] + [f'red{role}Rank' for role in roles]

# Failsafe, fill missing values with 0 (Unranked/No Mastery)
for col in mastery_cols + rank_cols:
    if col not in df.columns:
        df[col] = 0
    df[col] = df[col].fillna(0)

# Splitting and Scaling
logger.info("Splitting dataset and scaling...")
x_champs = df[all_cols]
x_synergies = df[['blueSynergy', 'redSynergy']]
x_meta = df[['blueTopMeta', 'blueJungleMeta', 'blueMidMeta', 'blueADCMeta', 'blueSupportMeta', 'redTopMeta', 'redJungleMeta', 'redMidMeta', 'redADCMeta', 'redSupportMeta']]
x_masteries = df[mastery_cols]
x_ranks = df[rank_cols]
y = df['blueWin']

x_c_train, x_c_test, x_s_train, x_s_test, x_m_train, x_m_test, x_mas_train, x_mas_test, x_rnk_train, x_rnk_test, y_train, y_test = train_test_split(
    x_champs, x_synergies, x_meta, x_masteries, x_ranks, y, test_size=0.2, random_state=42)

# Stack the 10 masteries and 10 ranks into a single 20-feature array
train_stats = np.hstack((x_mas_train, x_rnk_train))
test_stats = np.hstack((x_mas_test, x_rnk_test))

# Fit and transform the scaler on the 20-feature training block
scaler = StandardScaler()
scaled_train = scaler.fit_transform(train_stats)

# Transform only on the test block
scaled_test = scaler.transform(test_stats)

# Unpack them back into 10-feature blocks for the PyTorch DataLoader
x_mas_train = scaled_train[:, :10]
x_rnk_train = scaled_train[:, 10:]

x_mas_test = scaled_test[:, :10]
x_rnk_test = scaled_test[:, 10:]

os.makedirs("data/models", exist_ok=True)
joblib.dump(scaler, "data/models/scaler.pkl")

# Convert to Tensors
x_c_train_t = torch.tensor(x_c_train.values, dtype=torch.long)
x_s_train_t = torch.tensor(x_s_train.values, dtype=torch.float32)
x_m_train_t = torch.tensor(x_m_train.values, dtype=torch.float32)
x_mas_train_t = torch.tensor(x_mas_train, dtype=torch.float32)
x_rnk_train_t = torch.tensor(x_rnk_train, dtype=torch.float32)
y_train_t = torch.tensor(y_train.values, dtype=torch.float32).view(-1, 1)

x_c_test_t = torch.tensor(x_c_test.values, dtype=torch.long)
x_s_test_t = torch.tensor(x_s_test.values, dtype=torch.float32)
x_m_test_t = torch.tensor(x_m_test.values, dtype=torch.float32)
x_mas_test_t = torch.tensor(x_mas_test, dtype=torch.float32)
x_rnk_test_t = torch.tensor(x_rnk_test, dtype=torch.float32)
y_test_t = torch.tensor(y_test.values, dtype=torch.float32).view(-1, 1)

#Dynamic Batch scaling
total_matches = len(df)
if total_matches < 5000:
    dynamic_batch = 64     # Small datasets need smaller batches to learn effectively
elif total_matches < 25000:
    dynamic_batch = 128    # Medium datasets
elif total_matches < 100000:
    dynamic_batch = 256    # Large datasets
else:
    dynamic_batch = 512    # Massive datasets

logger.info(f"Dynamically set batch size to {dynamic_batch} based on {total_matches} total matches.")

# Pack DataLoaders
train_dataset = TensorDataset(x_c_train_t, x_s_train_t, x_m_train_t, x_mas_train_t, x_rnk_train_t, y_train_t)
train_loader = DataLoader(train_dataset, batch_size=dynamic_batch, shuffle=True, drop_last=True, num_workers=0)

test_dataset = TensorDataset(x_c_test_t, x_s_test_t, x_m_test_t, x_mas_test_t, x_rnk_test_t, y_test_t)
test_loader = DataLoader(test_dataset, batch_size=dynamic_batch, shuffle=False, num_workers=0)

# Initialize Model
model = Model(num_unique_champions, embedding_dim=config.EMBEDDING_DIM, dropout_rate=config.DROPOUT_RATE)
model.to(device)
criterion = nn.BCELoss()

# Check for existing model weights to enable continuous learning, but with a very cautious learning rate to protect old knowledge
model_path = "data/models/Lol_draft_predictor.safetensors"
optimizer_path = "data/models/optimizer.pt"

if os.path.exists(model_path):
    logger.info("Existing brain found! Loading previous weights for continuous learning...")
    state_dict = load_file(model_path)
    model.load_state_dict(state_dict)

    # Use a highly restrained learning rate to protect old knowledge
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005, weight_decay=1e-4)

    if os.path.exists(optimizer_path):
        optimizer.load_state_dict(torch.load(optimizer_path, map_location=device, weights_only=True))
else:
    logger.info("No existing brain found. Initializing a fresh neural network...")
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)

logger.info(f"Number of input columns: {x_champs.shape[1]}")
logger.info(f"Total Unique Champions found: {num_unique_champions}")
logger.info(f"Training on {len(x_c_train)} matches, Validating on {len(x_c_test)} matches...\n")

# Dynamic Patience Scaling
best_val_loss = float('inf')
patience = 5 if total_matches < 20000 else 8 # More data can handle a bit more patience to find those rare learning moments
patience_counter = 0
num_epochs = 50 if total_matches < 20000 else 100 # More epochs for larger datasets to allow the model to fully learn complex patterns

for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for batch_c, batch_s, batch_m, batch_mas, batch_rnk, batch_y in train_loader:
        # Teleporting every single data batch to the hardware accelerator
        batch_c, batch_s, batch_m = batch_c.to(device), batch_s.to(device), batch_m.to(device)
        batch_mas, batch_rnk, batch_y = batch_mas.to(device), batch_rnk.to(device), batch_y.to(device)

        optimizer.zero_grad()
        loss = criterion(model(batch_c, batch_s, batch_m, batch_mas, batch_rnk), batch_y)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    avg_train_loss = running_loss / len(train_loader)

    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for batch_c, batch_s, batch_m, batch_mas, batch_rnk, batch_y in test_loader:
            # Teleport validation batches to hardware accelerator
            batch_c, batch_s, batch_m = batch_c.to(device), batch_s.to(device), batch_m.to(device)
            batch_mas, batch_rnk, batch_y = batch_mas.to(device), batch_rnk.to(device), batch_y.to(device)

            loss = criterion(model(batch_c, batch_s, batch_m, batch_mas, batch_rnk), batch_y)
            val_loss += loss.item()

    avg_val_loss = val_loss / len(test_loader)

    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        patience_counter = 0

        # Saving the model and the optimizer's momentum
        save_file(model.state_dict(), model_path)
        torch.save(optimizer.state_dict(), optimizer_path)
        logger.info(f"Epoch [{epoch + 1}/{num_epochs}]  |  Train Loss: {avg_train_loss:.4f}  |  Val Loss: {avg_val_loss:.4f} (New Best!)")
    else:
        patience_counter += 1
        logger.info(f"Epoch [{epoch + 1}/{num_epochs}]  |  Train Loss: {avg_train_loss:.4f}  |  Val Loss: {avg_val_loss:.4f}  |  Strikes: {patience_counter}/{patience}")

        if patience_counter >= patience:
            logger.info(f"\nEarly stopping triggered! AI peaked at Epoch {epoch + 1 - patience}.")
            break

# Evaluation & Confusion Matrix
model.eval()
with torch.no_grad():
    # Moving full test dataset to device for final prediction
    x_c_test_t, x_s_test_t, x_m_test_t = x_c_test_t.to(device), x_s_test_t.to(device), x_m_test_t.to(device)
    x_mas_test_t, x_rnk_test_t = x_mas_test_t.to(device), x_rnk_test_t.to(device)

    predictions = model(x_c_test_t, x_s_test_t, x_m_test_t, x_mas_test_t, x_rnk_test_t)
    predicted_classes = (predictions >= 0.5).float()

# Calculate and print accuracy!
y_true = y_test_t.cpu().numpy()
y_pred = predicted_classes.cpu().numpy()

acc = accuracy_score(y_true, y_pred) * 100
logger.info(f"\nFinal Test Accuracy: {acc:.2f}%")

cm = confusion_matrix(y_true, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Red Win', 'Blue Win'])

fig, ax = plt.subplots(figsize=(8, 6))
disp.plot(cmap=plt.cm.Blues, ax=ax)
plt.title('AI Draft Predictor - Confusion Matrix')
os.makedirs("data/results", exist_ok=True)
plt.savefig('data/results/confusion_matrix.png', dpi=300, bbox_inches='tight')
plt.close()

logger.info("Confusion matrix saved as 'confusion_matrix.png'")