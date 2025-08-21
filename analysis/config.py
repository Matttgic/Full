# Configuration for the Match Analyzer Tool

# --- File Paths ---
ODDS_DATA_DIR = 'data/odds/raw_data'
MATCH_DATA_DIR = 'data/matches'
PROCESSED_DATA_PATH = 'data/analysis_data.parquet'

# --- API Configuration ---
# The RapidAPI key should be stored as an environment variable or a secret,
# not hardcoded here. We can add a function to load it.
RAPIDAPI_KEY = None

# --- Analysis Parameters ---
# The tolerance for considering odds as "similar".
# For example, 0.10 means a historic odd of 1.50 is a match for a target odd of 1.40 to 1.60.
SIMILARITY_THRESHOLD = 0.10

# The minimum number of bookmakers that must have odds on a market for it to be included.
MIN_BOOKMAKERS_THRESHOLD = 5
