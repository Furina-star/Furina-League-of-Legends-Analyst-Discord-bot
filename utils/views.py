"""
Button and dropdowns like that should be here, so that they can be easily imported and used in cogs and other places.
"""

import discord

# This class handles the button for '/ predict'
class PredictView(discord.ui.View):
    def __init__(self, blue_embed: discord.Embed, red_embed: discord.Embed):
        super().__init__(timeout=180)
        self.blue_embed = blue_embed
        self.red_embed = red_embed

    @discord.ui.button(label="Blue Team Draft", style=discord.ButtonStyle.blurple, custom_id="btn_blue")
    async def blue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Instantly swap the embed to the Blue Team version
        await interaction.response.edit_message(embed=self.blue_embed)

    @discord.ui.button(label="Red Team Draft", style=discord.ButtonStyle.red, custom_id="btn_red")
    async def red_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Instantly swap the embed to the Red Team version
        await interaction.response.edit_message(embed=self.red_embed)