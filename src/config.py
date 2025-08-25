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
