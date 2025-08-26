# Configuration for the Match Analyzer Tool

# --- File Paths ---
ODDS_DATA_DIR = 'data/odds/raw_data'
MATCH_DATA_DIR = 'data/matches'
PROCESSED_DATA_PATH = 'data/analysis_data.parquet'

# --- API Configuration ---
# The RapidAPI key should be stored as an environment variable or a secret.
RAPIDAPI_KEY = None

# --- Analysis Parameters ---

# The list of key structural bet types to use for the similarity analysis.
# This prevents player-specific or other obscure bets from polluting the comparison.
KEY_BET_TYPES = [
    "Match Winner",
    "Over/Under",
    "Both Teams to Score",
    "Double Chance",
    "Correct Score",
    "Half Time/Full Time"
]

# The tolerance for considering odds as "similar".
# For example, 0.10 means a historic odd of 1.50 is a match for a target odd of 1.40 to 1.60.
SIMILARITY_THRESHOLD = 0.10

# The minimum number of bookmakers that must have odds on a market for it to be included.
MIN_BOOKMAKERS_THRESHOLD = 3

# The minimum number of similar historical matches required to make a prediction.
# This prevents making high-confidence predictions from a small sample size.
MIN_SIMILAR_MATCHES_THRESHOLD = 10

# The minimum similarity percentage required to consider a prediction valid.
MIN_SIMILARITY_PCT_THRESHOLD = 70

# --- Data Collection Parameters ---

# Seasons to collect data for
SEASONS_TO_COLLECT = [2024, 2025]

# The list of all leagues to be processed by the system.
# This is the single source of truth for league information.
ALL_LEAGUES = {
    # Big 5
    'ENG1': {'id': 39, 'name': 'Premier League', 'country': 'England'},
    'FRA1': {'id': 61, 'name': 'Ligue 1', 'country': 'France'},
    'ITA1': {'id': 135, 'name': 'Serie A', 'country': 'Italy'},
    'GER1': {'id': 78, 'name': 'Bundesliga', 'country': 'Germany'},
    'SPA1': {'id': 140, 'name': 'La Liga', 'country': 'Spain'},
    # Extended Leagues
    'NED1': {'id': 88, 'name': 'Eredivisie', 'country': 'Netherlands'},
    'POR1': {'id': 94, 'name': 'Primeira Liga', 'country': 'Portugal'},
    'BEL1': {'id': 144, 'name': 'Jupiler Pro League', 'country': 'Belgium'},
    'ENG2': {'id': 40, 'name': 'Championship', 'country': 'England'},
    'FRA2': {'id': 62, 'name': 'Ligue 2', 'country': 'France'},
    'ITA2': {'id': 136, 'name': 'Serie B', 'country': 'Italy'},
    'GER2': {'id': 79, 'name': '2. Bundesliga', 'country': 'Germany'},
    'SPA2': {'id': 141, 'name': 'Segunda División', 'country': 'Spain'},
    'TUR1': {'id': 203, 'name': 'Süper Lig', 'country': 'Turkey'},
    'SAU1': {'id': 307, 'name': 'Saudi Pro League', 'country': 'Saudi Arabia'}
}
