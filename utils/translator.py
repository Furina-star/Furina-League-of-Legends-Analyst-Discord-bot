"""
Translator module for translating text using a static dictionary
This module provides a function to translate text from one language to another using the TRANSLATIONS dictionary.
The TRANSLATIONS dictionary contains mappings of original English text to their translations in various languages, keyed by the Discord locale.
The Translator class implements the app_commands.
Translator interface and uses the TRANSLATIONS dictionary to return the appropriate translation based on the user's locale.
If a translation is not available for a given string or locale, it returns None, allowing Discord to fall back to the default English text.
"""

import discord
from discord import app_commands

# We will translate the bot into Spanish as an example!
TRANSLATIONS = {
    # Spanish (Europe & Latin America)
    discord.Locale.spain_spanish: {
        "predict": "predecir",
        "Calculates win probability for a live match.": "Calcula la probabilidad de victoria para una partida en vivo.",
        "scout": "explorar",
        "Builds an enemy dossier for a live match.": "Crea un informe del equipo enemigo para una partida en vivo.",
        "The server region (e.g., NA1, EUW1, KR)": "La región del servidor (ej., NA1, EUW1, KR)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "El Riot ID del jugador (ej., Doublelift#NA1)"
    },
    discord.Locale.latin_american_spanish: {
        "predict": "predecir",
        "Calculates win probability for a live match.": "Calcula la probabilidad de victoria para una partida en vivo.",
        "scout": "explorar",
        "Builds an enemy dossier for a live match.": "Crea un informe del equipo enemigo para una partida en vivo.",
        "The server region (e.g., NA1, EUW1, KR)": "La región del servidor (ej., NA1, EUW1, KR)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "El Riot ID del jugador (ej., Doublelift#NA1)"
    },

    # Portuguese (Brazil)
    discord.Locale.brazil_portuguese: {
        "predict": "prever",
        "Calculates win probability for a live match.": "Calcula a probabilidade de vitória de uma partida ao vivo.",
        "scout": "analisar",
        "Builds an enemy dossier for a live match.": "Cria um dossiê da equipe inimiga para uma partida ao vivo.",
        "The server region (e.g., NA1, EUW1, KR)": "A região do servidor (ex: BR1, NA1, EUW1)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "O Riot ID do jogador (ex: Yoda#BR1)"
    },

    # French (Europe & Canada)
    discord.Locale.french: {
        "predict": "predire",
        "Calculates win probability for a live match.": "Calcule la probabilité de victoire pour un match en direct.",
        "scout": "analyser",
        "Builds an enemy dossier for a live match.": "Crée un dossier sur l'équipe ennemie pour un match en direct.",
        "The server region (e.g., NA1, EUW1, KR)": "La région du serveur (ex: NA1, EUW1, KR)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "Le Riot ID du joueur (ex: Doublelift#NA1)"
    },

    # German (Europe)
    discord.Locale.german: {
        "predict": "vorhersagen",
        "Calculates win probability for a live match.": "Berechnet die Gewinnwahrscheinlichkeit für ein Live-Spiel.",
        "scout": "ausspähen",
        "Builds an enemy dossier for a live match.": "Erstellt eine Analyse des gegnerischen Teams für ein Live-Spiel.",
        "The server region (e.g., NA1, EUW1, KR)": "Die Serverregion (z.B. EUW1, NA1, KR)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "Die Riot-ID des Spielers (z.B. Doublelift#NA1)"
    },

    # Polish (Europe)
    discord.Locale.polish: {
        "predict": "przewiduj",
        "Calculates win probability for a live match.": "Oblicza prawdopodobieństwo wygranej w meczu na żywo.",
        "scout": "zwiad",
        "Builds an enemy dossier for a live match.": "Tworzy raport o drużynie przeciwnej w meczu na żywo.",
        "The server region (e.g., NA1, EUW1, KR)": "Region serwera (np. EUNE1, EUW1, NA1)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "Riot ID gracza (np. Jankos#EUW)"
    },

    # Turkish (Turkey)
    discord.Locale.turkish: {
        "predict": "tahmin",
        "Calculates win probability for a live match.": "Canlı bir maç için kazanma olasılığını hesaplar.",
        "scout": "istihbarat",
        "Builds an enemy dossier for a live match.": "Canlı bir maç için rakip takım analizi oluşturur.",
        "The server region (e.g., NA1, EUW1, KR)": "Sunucu bölgesi (ör. TR1, EUW1, NA1)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "Oyuncunun Riot Kimliği (ör. Closer#TR1)"
    },

    # Korean (South Korea)
    discord.Locale.korean: {
        "predict": "예측",
        "Calculates win probability for a live match.": "실시간 매치의 승리 확률을 계산합니다.",
        "scout": "전적검색",
        "Builds an enemy dossier for a live match.": "실시간 매치의 적 팀 전적을 분석합니다.",
        "The server region (e.g., NA1, EUW1, KR)": "서버 지역 (예: KR, NA1, EUW1)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "플레이어의 라이엇 ID (예: Faker#KR1)"
    },

    # Japanese (Japan)
    discord.Locale.japanese: {
        "predict": "予測",
        "Calculates win probability for a live match.": "ライブマッチの勝率を計算します。",
        "scout": "偵察",
        "Builds an enemy dossier for a live match.": "ライブマッチの敵チーム情報を分析します。",
        "The server region (e.g., NA1, EUW1, KR)": "サーバー地域（例: JP1, KR, NA1）",
        "The player's Riot ID (e.g., Doublelift#NA1)": "プレイヤーのRiot ID（例: Evi#JP1）"
    },

    # Vietnamese (Vietnam / SEA)
    discord.Locale.vietnamese: {
        "predict": "dudoan",
        "Calculates win probability for a live match.": "Tính toán tỷ lệ thắng cho một trận đấu trực tiếp.",
        "scout": "trinhsat",
        "Builds an enemy dossier for a live match.": "Tạo hồ sơ đội địch cho một trận đấu trực tiếp.",
        "The server region (e.g., NA1, EUW1, KR)": "Khu vực máy chủ (vd: VN2, NA1, KR)",
        "The player's Riot ID (e.g., Doublelift#NA1)": "Riot ID của người chơi (vd: Levi#VN2)"
    },

    # Traditional Chinese (Taiwan / HK / Macao)
    discord.Locale.taiwan_chinese: {
        "predict": "預測",
        "Calculates win probability for a live match.": "計算即時對戰的勝率。",
        "scout": "偵察",
        "Builds an enemy dossier for a live match.": "分析即時對戰中的敵方隊伍資料。",
        "The server region (e.g., NA1, EUW1, KR)": "伺服器地區（例如：TW2, KR, NA1）",
        "The player's Riot ID (e.g., Doublelift#NA1)": "玩家的 Riot ID（例如：Karsa#TW2）"
    },

    # Simplified Chinese (China)
    discord.Locale.chinese: {
        "predict": "预测",
        "Calculates win probability for a live match.": "计算实时对战的胜率。",
        "scout": "侦察",
        "Builds an enemy dossier for a live match.": "分析实时对战中的敌方队伍数据。",
        "The server region (e.g., NA1, EUW1, KR)": "服务器地区（例如：NA1, KR, EUW1）",
        "The player's Riot ID (e.g., Doublelift#NA1)": "玩家的 Riot ID（例如：Uzi#CN1）"
    }
}

class DiscordTranslator(app_commands.Translator):
    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext) -> str | None:
        # Check if the user's language is in our dictionary
        if locale in TRANSLATIONS:
            # Return Translations, Default English
            return TRANSLATIONS[locale].get(string.message)
        return None