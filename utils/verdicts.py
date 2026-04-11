"""
A sole helper function to generate a post-game review verdict for Furina, the Roast Bot.
This function takes in a dictionary of match statistics and uses the RoastGenerator to apply all relevant roasts based on the player's performance.
If no specific roasts apply, it provides a generic verdict based on whether the player won or lost.
The function also handles cases where the combined roast exceeds Discord's embed character limit by adding a humorous suffix.
"""

import random
from utils.roasts import RoastGenerator


# Verdicts for post game review
def generate_furina_verdict(stats: dict) -> str:
    # Initialize the Roast Engine
    engine = RoastGenerator(stats)

    # Collect all matches instead of stopping at the first one
    applied_roasts = []
    for condition, verdict in engine.get_all_rules():
        if condition():
            applied_roasts.append(verdict)

    # If no condition met get the generic win and loss verdicts
    if not applied_roasts:
        return engine.get_fallback_quote()

    # (The [:1024] protects the bot from crashing Discord's embed character limit)
    combo_roast = " ".join(applied_roasts)
    if len(combo_roast) > 1024:
        suffixes = [
            "... And so much more. Truly a performance for the ages.",
            "... The list goes on, but I am simply too exhausted to continue.",
            "... I could keep going, but frankly, you are not worth my breath.",
            "... A tragedy so long, Discord physically will not let me finish it.",
            "... And that is only half of it. Please, log off and reflect on your choices.",
            "... I have run out of breath. Just uninstall the game.",
            "... I would list the rest of your blunders, but the audience is already leaving. What an absolute farce.",
            "... The Oratrice Mecanique d'Analyse Cardinale has quite literally overheated trying to process the sheer volume of your crimes. I rest my case.",
            "... To recount the entirety of this tragedy would take a full theatrical season. Let us just draw the curtains and pretend this never happened."
        ]

        # Choose a random suffix to add some variety to the bot's responses when the roast is too long
        chose_suffix = random.choice(suffixes)

        # Calculate how many characters we have left for the roast after adding the suffix
        safe_cut = 1020 - len(chose_suffix)
        raw_cut = combo_roast[:safe_cut]

        # Walk backward to the last space so we don't chop a word in half!
        clean_cut = raw_cut.rsplit(' ', 1)[0]

        return clean_cut + chose_suffix

    return combo_roast