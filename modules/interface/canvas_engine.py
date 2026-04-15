"""
This module provides a canvas engine for creating and manipulating images using the Pillow library.
It allows you to create a canvas, draw shapes, add text, and save the resulting image.
The engine is designed to be used in an asynchronous context, making it suitable for applications that require non-blocking operations.
"""

import os
import io
import asyncio
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont

# Configuration & Constants
CACHE_DIR = "data/img_cache"
ASSETS_DIR = "data/assets"
os.makedirs(CACHE_DIR, exist_ok=True)

# Strict Color Palette
WHITE_TEXT = (255, 255, 255)
GOLD_TEXT = (255, 215, 0)
BLUE_TEXT = (43, 109, 240)
RED_TEXT = (240, 43, 43)
DIM_TEXT = (114, 118, 125)
BG_COLOR = (43, 45, 49, 255)
SHADOW_COLOR = (0, 0, 0, 200)

_ASSET_CACHE = {}

# Get the Data Dragon patch for this file dynamically
async def _get_patch_version(session: aiohttp.ClientSession) -> str:
    if "patch_version" not in _ASSET_CACHE:
        try:
            async with session.get("https://ddragon.leagueoflegends.com/api/versions.json") as resp:
                if resp.status == 200:
                    versions = await resp.json()
                    _ASSET_CACHE["patch_version"] = versions[0]
                else:
                    _ASSET_CACHE["patch_version"] = "14.8.1"
        except aiohttp.ClientError:
            _ASSET_CACHE["patch_version"] = "14.8.1"
    return _ASSET_CACHE["patch_version"]

# Helper to load and cache fonts in memory.
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    cache_key = f"font_{size}"
    if cache_key not in _ASSET_CACHE:
        try:
            _ASSET_CACHE[cache_key] = ImageFont.truetype(f"{ASSETS_DIR}/BeaufortForLOL-Bold.ttf", size)
        except OSError:
            try:
                _ASSET_CACHE[cache_key] = ImageFont.truetype("arial.ttf", size)
            except OSError:
                _ASSET_CACHE[cache_key] = ImageFont.load_default()
    return _ASSET_CACHE[cache_key]

# Helper to load, composite, and cache the background image.
def _get_background() -> Image.Image:
    if "bg" not in _ASSET_CACHE:
        bg_path = f"{ASSETS_DIR}/background.jpg"
        if os.path.exists(bg_path):
            background = Image.open(bg_path).convert("RGBA").resize((800, 660))
            overlay = Image.new("RGBA", (800, 660), (0, 0, 0, 80))
            _ASSET_CACHE["bg"] = Image.alpha_composite(background, overlay)
        else:
            _ASSET_CACHE["bg"] = Image.new("RGBA", (800, 660), BG_COLOR)
    return _ASSET_CACHE["bg"].copy()

# Helper to cache the gold selection border.
def _get_select_icon() -> Image.Image | None:
    if "select_icon" not in _ASSET_CACHE:
        try:
            _ASSET_CACHE["select_icon"] = Image.open(f"{ASSETS_DIR}/champion_series_icon.png").convert("RGBA").resize(
                (80, 80))
        except OSError:
            _ASSET_CACHE["select_icon"] = None
    return _ASSET_CACHE["select_icon"]

# Helper to cache the champion icon rounded edge mask.
def _get_rounded_mask() -> Image.Image:
    if "mask" not in _ASSET_CACHE:
        mask = Image.new("L", (80, 80), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 80, 80), radius=12, fill=255)
        _ASSET_CACHE["mask"] = mask
    return _ASSET_CACHE["mask"]

# Helper to cache a smaller rounded mask for banned champions
def _get_ban_mask() -> Image.Image:
    if "ban_mask" not in _ASSET_CACHE:
        mask = Image.new("L", (45, 45), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 45, 45), radius=8, fill=255)
        _ASSET_CACHE["ban_mask"] = mask
    return _ASSET_CACHE["ban_mask"]

# Asynchronous Data Fetching
async def fetch_icon(session: aiohttp.ClientSession, champ: str) -> Image.Image:
    if champ == "Unknown" or "(You)" in champ:
        return Image.new("RGBA", (80, 80), BG_COLOR)

    filepath = os.path.join(CACHE_DIR, f"{champ}.png")

    if not os.path.exists(filepath):
        patch_version = await _get_patch_version(session)
        url = f"https://ddragon.leagueoflegends.com/cdn/{patch_version}/img/champion/{champ}.png"

        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                async with aiofiles.open(filepath, "wb") as f:
                    await f.write(data)
            else:
                return Image.new("RGBA", (80, 80), BG_COLOR)

    return Image.open(filepath).convert("RGBA").resize((80, 80))

# Helper to perfectly center and shadow title text.
def _draw_centered_header(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font: ImageFont.FreeTypeFont, fill: tuple):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((x - w / 2 + 2, y + 2), text, fill=SHADOW_COLOR, font=font)
    draw.text((x - w / 2, y), text, fill=fill, font=font)

# Helper to determine the display text and color for each slot, reducing complexity in the main drawing loop.
def _resolve_slot_visuals(current_val: str, pos: str, is_user: bool, team_name: str) -> tuple[str, tuple]:
    if current_val == "Unknown":
        formatted_pos = "ADC" if pos == "adc" else pos.title()
        return f"[{formatted_pos}]", (GOLD_TEXT if is_user else WHITE_TEXT)

    text = f"{current_val} (You)" if is_user else current_val
    color = BLUE_TEXT if team_name == "Blue" else RED_TEXT
    return text, color

# Helper to draw either the Blue or Red side columns using the exact same logic.
def _draw_team_column(canvas: Image.Image, draw: ImageDraw.ImageDraw, icons: list, team_dict: dict, role: str, user_team: str, team_name: str, x_offset: int, align: str):
    y = 100
    positions = ['top', 'jungle', 'mid', 'adc', 'support']

    mask = _get_rounded_mask()
    select_icon = _get_select_icon()
    font = _get_font(28)

    for i, icon in enumerate(icons):
        canvas.paste(icon, (x_offset, y), mask)

        is_user_slot = (user_team == team_name and positions[i] == role)
        if is_user_slot and select_icon:
            canvas.paste(select_icon, (x_offset, y), select_icon)

        # 🔥 Relies on new helper for reduced complexity
        display_text, text_color = _resolve_slot_visuals(team_dict[positions[i]], positions[i], is_user_slot, team_name)

        if align == "left":
            text_x = x_offset + 100
        else:
            text_bbox = draw.textbbox((0, 0), display_text, font=font)
            text_x = x_offset - 20 - (text_bbox[2] - text_bbox[0])

        draw.text((text_x + 2, y + 27), display_text, fill=SHADOW_COLOR, font=font)
        draw.text((text_x, y + 25), display_text, fill=text_color, font=font)

        y += 90

# Main Execution Engine
async def render_draft_board(blue_dict: dict, red_dict: dict, role: str, user_team: str, banned_champs: list = None) -> io.BytesIO:
    if banned_champs is None:
        banned_champs = []

    canvas = _get_background()
    draw = ImageDraw.Draw(canvas)

    _draw_centered_header(draw, "BLUE TEAM", 200, 30, _get_font(36), BLUE_TEXT)
    _draw_centered_header(draw, "RED TEAM", 600, 30, _get_font(36), RED_TEXT)
    _draw_centered_header(draw, "VS", 400, 42, _get_font(58), GOLD_TEXT)

    positions = ['top', 'jungle', 'mid', 'adc', 'support']
    async with aiohttp.ClientSession() as session:
        blue_icons = await asyncio.gather(*[fetch_icon(session, blue_dict[p]) for p in positions])
        red_icons = await asyncio.gather(*[fetch_icon(session, red_dict[p]) for p in positions])
        ban_icons = await asyncio.gather(*[fetch_icon(session, champ) for champ in banned_champs])

    _draw_team_column(canvas, draw, blue_icons, blue_dict, role, user_team, "Blue", 40, "left")
    _draw_team_column(canvas, draw, red_icons, red_dict, role, user_team, "Red", 680, "right")

    # Draw the Banned Champions Section!
    _draw_centered_header(draw, "BANNED CHAMPIONS", 400, 565, _get_font(24), DIM_TEXT)

    # Banning algorithm
    ban_size = 45
    spacing = 15
    total_slots = 10

    # Calculate perfect centering for exactly 10 slots
    total_w = total_slots * ban_size + (total_slots - 1) * spacing
    start_x = int(400 - (total_w / 2))
    ban_mask = _get_ban_mask()

    for i in range(total_slots):
        x = start_x + i * (ban_size + spacing)
        y = 600

        if i < len(banned_champs):
            # Draw locked ban
            small_icon = ban_icons[i].resize((ban_size, ban_size), Image.Resampling.LANCZOS)
            grayscale = small_icon.convert("LA").convert("RGBA")
            canvas.paste(grayscale, (x, y), ban_mask)

            draw.line((x + 4, y + ban_size - 4, x + ban_size - 4, y + 4), fill=(240, 43, 43, 230), width=4)
        else:
            draw.rounded_rectangle(
                (x, y, x + ban_size, y + ban_size),
                radius=8,
                fill=(30, 32, 36, 180),
                outline=(80, 84, 92, 200),
                width=2
            )

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer