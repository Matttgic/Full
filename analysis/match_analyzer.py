import pandas as pd
import os
import glob
import numpy as np
import logging
import argparse
import requests
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_all_csvs(directory_path: str) -> pd.DataFrame:
    """Loads and concatenates all CSV files from a given directory."""
    all_files = glob.glob(os.path.join(directory_path, "*.csv"))
    if not all_files:
        logging.warning(f"No CSV files found in directory: {directory_path}")
        return pd.DataFrame()

    df_list = [pd.read_csv(file, low_memory=False) for file in all_files]
    return pd.concat(df_list, ignore_index=True)

def create_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a feature matrix from raw odds data.
    - Calculates the mean odds for each bet type per fixture.
    - Pivots the table to have one row per fixture and columns for each bet.
    """
    if df.empty:
        return pd.DataFrame()

    df['bet_identifier'] = df['bet_type_name'] + '_' + df['bet_value'].astype(str)

    # Filter out bets with too few bookmakers for reliability
    bookmaker_counts = df.groupby(['fixture_id', 'bet_identifier'])['bookmaker_id'].nunique().reset_index()
    reliable_bets = bookmaker_counts[bookmaker_counts['bookmaker_id'] >= config.MIN_BOOKMAKERS_THRESHOLD]
    reliable_df = pd.merge(df, reliable_bets[['fixture_id', 'bet_identifier']], on=['fixture_id', 'bet_identifier'])

    mean_odds = reliable_df.groupby(['fixture_id', 'bet_identifier'])['odd'].mean().reset_index()

    feature_matrix = mean_odds.pivot(index='fixture_id', columns='bet_identifier', values='odd')

    logging.info(f"Created feature matrix with shape: {feature_matrix.shape}")
    return feature_matrix

def get_match_results(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts final match results (who won)."""
    if df.empty:
        return pd.DataFrame()

    results_df = df[['fixture_id', 'home_goals', 'away_goals']].copy()
    results_df.dropna(subset=['home_goals', 'away_goals'], inplace=True)

    conditions = [
        (results_df['home_goals'] > results_df['away_goals']),
        (results_df['home_goals'] < results_df['away_goals']),
    ]
    choices = ['Home', 'Away']
    results_df['result'] = np.select(conditions, choices, default='Draw')

    return results_df[['fixture_id', 'result']].drop_duplicates()

def preprocess_and_save_data():
    """Orchestrates the data loading and preprocessing, saving the result."""
    logging.info("Starting data preprocessing...")
    all_odds_df = load_all_csvs(config.ODDS_DATA_DIR)
    all_matches_df = load_all_csvs(config.MATCH_DATA_DIR)

    if all_odds_df.empty or all_matches_df.empty:
        logging.error("No data loaded. Halting preprocessing.")
        return

    feature_matrix = create_feature_matrix(all_odds_df)
    match_results = get_match_results(all_matches_df)

    final_df = pd.merge(feature_matrix, match_results, left_index=True, right_on='fixture_id', how='inner')
    final_df.set_index('fixture_id', inplace=True)

    try:
        final_df.to_parquet(config.PROCESSED_DATA_PATH)
        logging.info(f"Successfully saved analysis-ready data to {config.PROCESSED_DATA_PATH}")
    except Exception as e:
        logging.error(f"Failed to save data to Parquet file: {e}")

def get_api_odds_for_fixture(fixture_id: int) -> pd.DataFrame:
    """Fetches and processes odds for a single target fixture from the API."""
    logging.info(f"Fetching odds for target fixture: {fixture_id}")
    api_key = os.environ.get('RAPIDAPI_KEY', config.RAPIDAPI_KEY)
    if not api_key:
        raise ValueError("RapidAPI key not found in config or environment variables.")

    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    params = {'fixture': str(fixture_id)}
    headers = {
        'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
        'x-rapidapi-key': api_key
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()['response']

    processed_odds = []
    for odds_entry in data:
        for bookmaker in odds_entry.get('bookmakers', []):
            for bet in bookmaker.get('bets', []):
                for value in bet.get('values', []):
                    processed_odds.append({
                        'fixture_id': fixture_id,
                        'bet_type_name': bet['name'],
                        'bet_value': value['value'],
                        'odd': value['odd'],
                        'bookmaker_id': bookmaker['id']
                    })

    if not processed_odds:
        return pd.DataFrame()

    odds_df = pd.DataFrame(processed_odds)
    return create_feature_matrix(odds_df)

def find_similar_matches(target_vector: pd.Series, historical_matrix: pd.DataFrame, threshold: float):
    """Finds similar matches based on odds distance."""
    # Align columns - crucial for comparison
    common_bets = target_vector.index.intersection(historical_matrix.columns)

    if len(common_bets) == 0:
        logging.warning("No common bet types found between target and historical data.")
        return pd.Series(dtype=float)

    historical_aligned = historical_matrix[common_bets]
    target_aligned = target_vector[common_bets]

    # Calculate absolute difference and mean it
    # This is robust to missing data (NaNs)
    diff = np.abs(historical_aligned - target_aligned)
    distance = diff.mean(axis=1)

    # Filter by threshold
    similar_fixtures = distance[distance < threshold]
    return similar_fixtures.sort_values()

def analyze_fixture(fixture_id: int):
    """Main analysis workflow for a single fixture."""
    logging.info(f"--- Starting Analysis for Fixture ID: {fixture_id} ---")

    # 1. Load preprocessed historical data
    try:
        historical_df = pd.read_parquet(config.PROCESSED_DATA_PATH)
    except FileNotFoundError:
        logging.error(f"Processed data file not found at {config.PROCESSED_DATA_PATH}. Please run with --preprocess first.")
        return

    # 2. Get odds for the target fixture from the API
    target_odds_vector = get_api_odds_for_fixture(fixture_id)
    if target_odds_vector.empty:
        logging.error(f"Could not retrieve or process odds for fixture {fixture_id}.")
        return

    # 3. Find similar matches
    target_vector = target_odds_vector.iloc[0]
    historical_matrix = historical_df.drop(columns=['result'])

    similar_matches = find_similar_matches(target_vector, historical_matrix, config.SIMILARITY_THRESHOLD)

    if similar_matches.empty:
        logging.info("No historically similar matches found.")
        return

    logging.info(f"Found {len(similar_matches)} similar matches with an average distance < {config.SIMILARITY_THRESHOLD}.")

    # 4. Analyze the results of those similar matches
    similar_ids = similar_matches.index
    results_of_similar = historical_df.loc[similar_ids]['result']

    result_stats = results_of_similar.value_counts(normalize=True) * 100

    print("\n--- Analysis Report ---")
    print(f"Fixture ID: {fixture_id}")
    print(f"Found {len(similar_ids)} similar historical matches.")
    print("\nPredicted Outcome Probabilities:")
    for outcome, percentage in result_stats.items():
        print(f"  - {outcome}: {percentage:.2f}%")
    print("-----------------------\n")


def main():
    """Main entry point to run preprocessing or analysis."""
    parser = argparse.ArgumentParser(description="Football Match Odds Analyzer.")
    parser.add_argument('--preprocess', action='store_true', help="Run the data preprocessing and save the feature matrix.")
    parser.add_argument('--analyze', type=int, metavar='FIXTURE_ID', help="Analyze a specific fixture ID to find similar historical matches.")

    args = parser.parse_args()

    if args.preprocess:
        preprocess_and_save_data()
    elif args.analyze:
        analyze_fixture(args.analyze)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
