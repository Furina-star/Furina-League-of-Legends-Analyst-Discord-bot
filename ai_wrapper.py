"""
This is where AI logic functions are stored, such as loading the model, preprocessing the input, and calculating the win probabilities.
"""

import torch
import torch.nn as nn
from safetensors.torch import load_model
import json
from itertools import combinations
import logging
from typing import List, Tuple, Dict, Any

# Get the logging system
logger = logging.getLogger(__name__)

# Define the Model Architecture
class Model(nn.Module):
    def __init__(self, num_champions, embedding_dim=16, num_champs_in_match=10,
                 num_extra_features=12, dropout_rate=0.25):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_champions, embedding_dim=embedding_dim)

        input_size = (num_champs_in_match * embedding_dim) + num_extra_features

        self.net = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout_rate),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(dropout_rate),

            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x, synergy_scores, meta_rates):
        embedded = self.embedding(x)
        flattened = embedded.view(x.size(0), -1)
        combined = torch.cat((flattened, synergy_scores, meta_rates), dim=1)
        return self.net(combined)

def calculate_team_synergy(team_champs: List[str], synergy_matrix: Dict[str, Any], base_winrate: float) -> float:
    score = 0.0
    for duo in combinations(sorted(team_champs), 2):
        pair_key = f"{duo[0]}-{duo[1]}"

        if pair_key in synergy_matrix:
            score += (synergy_matrix[pair_key]["winrate"] - base_winrate)

    return score

# Wrapper Class
class LeagueAI:
    # This function set up and load Label encoder and the model
    def __init__(self,
                 bot_config: dict,
                 model_path: str = "models/Lol_draft_predictor.safetensors",
                 encoder_path: str = "models/champion_encoder.json",
                 synergy_path: str = "data/Synergy_Matrix.json",
                 meta_path: str = "data/Meta_Champions.json"):

        logger.info("Loading AI parameters...")
        self.config = bot_config
        self.ai_ready = False

        try:
            with open(synergy_path, "r") as f:
                self.synergy_matrix = json.load(f)
            with open(meta_path, "r") as f:
                self.meta_db = json.load(f)

            with open(encoder_path, "r") as f:
                self.champ_encoder = json.load(f)

            self.known_classes = set(self.champ_encoder.keys())

            num_champs = len(self.known_classes)
            self.model = Model(num_champions=num_champs, embedding_dim=self.config.get('EMBEDDING_DIM', 16), dropout_rate=self.config.get('DROPOUT_RATE', 0.25))
            load_model(self.model, model_path)
            self.model.eval()

            self.ai_ready = True
            logger.info("AI Model loaded successfully.")

        except Exception as e:
            logger.error(f"Failed to load AI components: {e}")

    # This function takes in a draft dictionary, preprocesses it, and returns the predicted win probability for the blue team
    def predict_match(self, draft_dict: Dict[str, str]) -> Tuple[float, float, float, float]:
        correct_order = [
            'blueTopChamp', 'blueJungleChamp', 'blueMiddleChamp', 'blueADCChamp', 'blueSupportChamp',
            'redTopChamp', 'redJungleChamp', 'redMiddleChamp', 'redADCChamp', 'redSupportChamp'
        ]

        raw_champs = [draft_dict[col] for col in correct_order]

        # Safe encoding that never crashes on 'unknown'
        encoded_list = [
            self.champ_encoder.get(champ, 0)
            for champ in raw_champs
        ]

        # Extract the raw champion names from the dictionary to calculate synergy.
        blue_champs = raw_champs[:5]
        red_champs = raw_champs[5:]

        # Calculate synergy scores for both teams using the synergy matrix
        blue_synergy = calculate_team_synergy(blue_champs, self.synergy_matrix, self.config['BASE_WINRATE'])
        red_synergy = calculate_team_synergy(red_champs, self.synergy_matrix, self.config['BASE_WINRATE'])

        meta_list = [self.meta_db.get(champ, self.config['BASE_WINRATE']) for champ in raw_champs]

        # Convert everything to tensors
        x_tensor = torch.tensor([encoded_list], dtype=torch.long)
        synergy_tensor = torch.tensor([[blue_synergy, red_synergy]], dtype=torch.float32)
        meta_tensor = torch.tensor([meta_list], dtype=torch.float32)

        with torch.no_grad():
            prediction = self.model(x_tensor, synergy_tensor, meta_tensor).item()

        return prediction, 1.0 - prediction, blue_synergy, red_synergy

    # This function batch 50 drafts and send it through the model exactly once
    def predict_batch(self, drafts_list: List[Dict[str, str]]) -> List[Tuple[float, float, float, float]]:
        all_encoded = []
        all_synergies = []
        all_metas = []

        correct_order = [
            'blueTopChamp', 'blueJungleChamp', 'blueMiddleChamp', 'blueADCChamp', 'blueSupportChamp',
            'redTopChamp', 'redJungleChamp', 'redMiddleChamp', 'redADCChamp', 'redSupportChamp'
        ]

        # Loop to gather data, NOT to run PyTorch
        for draft_dict in drafts_list:
            raw_champs = [draft_dict.get(col, 'Unknown') for col in correct_order]

            # Use the JSON dictionary we made earlier
            encoded_list = [self.champ_encoder.get(champ, 0) for champ in raw_champs]

            blue_champs = raw_champs[:5]
            red_champs = raw_champs[5:]

            # Use the injected config we made earlier
            blue_synergy = calculate_team_synergy(blue_champs, self.synergy_matrix, self.config['BASE_WINRATE'])
            red_synergy = calculate_team_synergy(red_champs, self.synergy_matrix, self.config['BASE_WINRATE'])

            meta_list = [self.meta_db.get(champ, self.config['BASE_WINRATE']) for champ in raw_champs]

            all_encoded.append(encoded_list)
            all_synergies.append([blue_synergy, red_synergy])
            all_metas.append(meta_list)

        if not drafts_list:
            return []

        # Convert everything into 3 giant tensors
        x_tensor = torch.tensor(all_encoded, dtype=torch.long)
        synergy_tensor = torch.tensor(all_synergies, dtype=torch.float32)
        meta_tensor = torch.tensor(all_metas, dtype=torch.float32)

        # Run the model exactly once
        with torch.no_grad():
            predictions = self.model(x_tensor, synergy_tensor, meta_tensor).squeeze(-1).tolist()

        # Failsafe if the batch only had 1 item and PyTorch stripped the list
        if isinstance(predictions, float):
            predictions = [predictions]

        # Package the results
        results = []
        for i in range(len(predictions)):
            pred = predictions[i]
            blue_syn = all_synergies[i][0]
            red_syn = all_synergies[i][1]
            results.append((pred, 1.0 - pred, blue_syn, red_syn))

        return results

    # This function calculates the winrates
    def apply_hybrid_algorithm(self, base_blue_prob: float, blue_winrates: List[float],
                               red_winrates: List[float], blue_masteries: List[int],
                               red_masteries: List[int]) -> Tuple[float, float]:

        avg_blue = sum(blue_winrates) / len(blue_winrates) if blue_winrates else 50.0
        avg_red = sum(red_winrates) / len(red_winrates) if red_winrates else 50.0

        skill_modifier = ((avg_blue - avg_red) * 0.5) / 100.0

        def calculate_mastery_modifier(masteries: List[int]) -> float:
            team_mod = 0.0
            for points in masteries:
                if points < self.config['FIRST_TIME_THRESHOLD']:
                    team_mod -= self.config['FIRST_TIME_PENALTY']
                elif points > self.config['OTP_THRESHOLD']:
                    extra_points = min(points, self.config['OTP_MAX_CAP']) - self.config['OTP_THRESHOLD']
                    team_mod += (extra_points / 100000) * self.config['OTP_BUFF_MULTIPLIER']
            return team_mod

        blue_x_factor = calculate_mastery_modifier(blue_masteries)
        red_x_factor = calculate_mastery_modifier(red_masteries)

        final_blue_prob = base_blue_prob + skill_modifier + blue_x_factor - red_x_factor
        final_blue_prob = max(0.01, min(0.99, final_blue_prob))

        return final_blue_prob, 1.0 - final_blue_prob

    # Sorts a list of champion names into standard [Top, Jgl, Mid, ADC, Sup] order
    @staticmethod
    def sort_draft_strings(draft_list: list, role_db: dict) -> list:
        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        sorted_draft = ["Unknown"] * 5
        champ_roles = LeagueAI.get_champ_roles(role_db)

        # Keep track of champions that need flexible placement
        flex_champs = []

        #Strict one-role champions ONLY
        for champ in draft_list:
            roles = [r for r in champ_roles.get(champ, []) if r in positions]

            # If they only have 1 valid role and the slot is empty, lock them in
            if len(roles) == 1 and sorted_draft[positions.index(roles[0])] == "Unknown":
                sorted_draft[positions.index(roles[0])] = champ
            else:
                flex_champs.append((champ, roles))

        # Greedily assign flexible champions
        for champ, roles in flex_champs:
            placed = False
            for role in roles:
                idx = positions.index(role)
                if sorted_draft[idx] == "Unknown":
                    sorted_draft[idx] = champ
                    placed = True
                    break

            # True fallback (if team comp is completely chaotic/off-meta)
            if not placed and "Unknown" in sorted_draft:
                empty_idx = sorted_draft.index("Unknown")
                sorted_draft[empty_idx] = champ

        return sorted_draft

    # Filters out invalid roles, picked champions, and banned champions
    @staticmethod
    def _get_valid_available_champions(target_role: str, role_db: dict, blue_dict: dict, red_dict: dict, banned_champs: list) -> list:
        champ_roles = LeagueAI.get_champ_roles(role_db)

        # Convert lists to a Set for lightning-fast O(1) lookups
        unavailable = set(blue_dict.values()) | set(red_dict.values()) | set(banned_champs)

        return [
            champ for champ, roles in champ_roles.items()
            if target_role in roles and champ not in unavailable
        ]

    # Constructs the exact dictionary format expected by the ML Model from the current draft state
    @staticmethod
    def _build_draft_input(blue_dict: dict, red_dict: dict) -> dict:
        return {
            'blueTopChamp': blue_dict.get('top', 'Unknown'),
            'blueJungleChamp': blue_dict.get('jungle', 'Unknown'),
            'blueMiddleChamp': blue_dict.get('mid', 'Unknown'),
            'blueADCChamp': blue_dict.get('adc', 'Unknown'),
            'blueSupportChamp': blue_dict.get('support', 'Unknown'),
            'redTopChamp': red_dict.get('top', 'Unknown'),
            'redJungleChamp': red_dict.get('jungle', 'Unknown'),
            'redMiddleChamp': red_dict.get('mid', 'Unknown'),
            'redADCChamp': red_dict.get('adc', 'Unknown'),
            'redSupportChamp': red_dict.get('support', 'Unknown')
        }

    # Calculates synergy and meta winrates to explain the decision.
    def _determine_pick_reason(self, champ: str, allies: list) -> str:
        best_syn_score = 0.0
        best_ally = ""

        # Check for high synergy with currently locked-in allies
        for ally in allies:
            pair = sorted([champ, ally])
            pair_key = f"{pair[0]}-{pair[1]}"
            if pair_key in self.synergy_matrix:
                syn_score = self.synergy_matrix[pair_key]["winrate"] - self.config['BASE_WINRATE']
                if syn_score > best_syn_score:
                    best_syn_score = syn_score
                    best_ally = ally

        if best_syn_score >= 0.015:
            return f"High synergy with {best_ally}."

        # Check if it's just a raw meta monster right now
        meta_wr = self.meta_db.get(champ, self.config['BASE_WINRATE'])
        if meta_wr >= 0.515:
            return f"Strong current meta pick ({meta_wr * 100:.1f}% WR)."

        return "Solid balanced addition."

    # The main function called by the draft coach command to get the top 3 champion suggestions for a given role and draft state.
    # Rapidly simulates the current draft state against all valid champions for a target role.
    def suggest_champion(self, target_role: str, user_team: str, blue_dict: dict, red_dict: dict, role_db: dict,
                         banned_champs: list = None):
        target_role = target_role.lower()
        is_blue = (user_team.lower() == 'blue')

        valid_champions = self._get_valid_available_champions(
            target_role, role_db, blue_dict, red_dict, banned_champs or []
        )

        allies = [c for c in (blue_dict.values() if is_blue else red_dict.values()) if c != "Unknown"]

        # Build the batch of drafts
        draft_batch = []
        for champ in valid_champions:
            test_blue, test_red = blue_dict.copy(), red_dict.copy()
            if is_blue:
                test_blue[target_role] = champ
            else:
                test_red[target_role] = champ
            draft_batch.append(self._build_draft_input(test_blue, test_red))

        if not draft_batch:
            return []

        # Send the entire batch to PyTorch at once
        try:
            batch_predictions = self.predict_batch(draft_batch)
        except Exception as e:
            logger.error(f"Batch AI Coach Simulation failed: {e}")
            return []

        # Process the results natively
        results = []
        for champ, prediction in zip(valid_champions, batch_predictions):
            win_prob = prediction[0] if is_blue else prediction[1]
            reason = self._determine_pick_reason(champ, allies)
            results.append((champ, win_prob, reason))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:3]

    # Translates the Riot Category DB into a Champion-First DB
    @staticmethod
    def get_champ_roles(role_db: dict) -> dict:
        inverted = {}
        mapping = {
            "top": ["KNOWN_TOPS"],
            "jungle": ["KNOWN_JUNGLES"],
            "mid": ["KNOWN_MIDS"],
            "adc": ["PURE_ADCS", "FLEX_BOTS"],
            "support": ["PURE_SUPPORTS", "FLEX_SUPPORTS"]
        }
        for standard_role, categories in mapping.items():
            for cat in categories:
                for champ in role_db.get(cat, []):
                    if champ not in inverted:
                        inverted[champ] = []
                    inverted[champ].append(standard_role)
        return inverted