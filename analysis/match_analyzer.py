import pandas as pd
import os
import glob
import numpy as np
import logging
import argparse
import requests
import json
from datetime import datetime
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
    - Filters for key bet types.
    - Calculates the mean odds for each bet type per fixture.
    - Pivots the table to have one row per fixture and columns for each bet.
    """
    if df.empty:
        return pd.DataFrame()

    df = df[df['bet_type_name'].isin(config.KEY_BET_TYPES)].copy()
    if df.empty:
        logging.warning("No data left after filtering for key bet types.")
        return pd.DataFrame()

    df['bet_identifier'] = df['bet_type_name'] + '_' + df['bet_value'].astype(str)

    bookmaker_counts = df.groupby(['fixture_id', 'bet_identifier'])['bookmaker_id'].nunique().reset_index()
    reliable_bets = bookmaker_counts[bookmaker_counts['bookmaker_id'] >= config.MIN_BOOKMAKERS_THRESHOLD]

    if reliable_bets.empty:
        logging.warning("No reliable bets found after MIN_BOOKMAKERS_THRESHOLD filter.")
        return pd.DataFrame()

    reliable_df = pd.merge(df, reliable_bets[['fixture_id', 'bet_identifier']], on=['fixture_id', 'bet_identifier'])

    if reliable_df.empty:
        return pd.DataFrame()

    mean_odds = reliable_df.groupby(['fixture_id', 'bet_identifier'])['odd'].mean().reset_index()

    feature_matrix = mean_odds.pivot(index='fixture_id', columns='bet_identifier', values='odd')

    logging.info(f"Created feature matrix with shape: {feature_matrix.shape}")
    return feature_matrix

def get_match_results(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts final match results."""
    if df.empty:
        return pd.DataFrame()

    results_df = df[['fixture_id', 'home_team_name', 'away_team_name', 'home_goals', 'away_goals']].copy()
    results_df.dropna(subset=['home_goals', 'away_goals'], inplace=True)

    conditions = [
        (results_df['home_goals'] > results_df['away_goals']),
        (results_df['home_goals'] < results_df['away_goals']),
    ]
    choices = ['Home', 'Away']
    results_df['result'] = np.select(conditions, choices, default='Draw')

    return results_df[['fixture_id', 'home_team_name', 'away_team_name', 'result']].drop_duplicates()

def preprocess_and_save_data():
    """Orchestrates the data loading and preprocessing."""
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
    """Fetches and processes odds for a single target fixture."""
    logging.info(f"Fetching odds for target fixture: {fixture_id}")
    api_key = os.environ.get('RAPIDAPI_KEY', config.RAPIDAPI_KEY)
    if not api_key:
        raise ValueError("RapidAPI key not found.")

    response = requests.get(
        "https://api-football-v1.p.rapidapi.com/v3/odds",
        params={'fixture': str(fixture_id)},
        headers={'x-rapidapi-host': "api-football-v1.p.rapidapi.com", 'x-rapidapi-key': api_key}
    )
    response.raise_for_status()
    data = response.json()['response']

    processed_odds = [{'fixture_id': fixture_id, 'bet_type_name': bet['name'], 'bet_value': value['value'], 'odd': value['odd'], 'bookmaker_id': bookmaker['id']} for odds_entry in data for bookmaker in odds_entry.get('bookmakers', []) for bet in bookmaker.get('bets', []) for value in bet.get('values', [])]

    return create_feature_matrix(pd.DataFrame(processed_odds)) if processed_odds else pd.DataFrame()

def find_similar_matches(target_vector: pd.Series, historical_matrix: pd.DataFrame):
    """Finds similar matches and returns the full distance series."""
    common_bets = target_vector.index.intersection(historical_matrix.columns)
    logging.info(f"Found {len(common_bets)} common bet types for comparison.")

    if len(common_bets) < 5: # Add a sanity check
        logging.warning("Too few common bet types to make a reliable comparison.")
        return pd.Series(dtype=float), common_bets.tolist()

    historical_aligned = historical_matrix[common_bets]
    target_aligned = target_vector[common_bets]

    distance = np.abs(historical_aligned - target_aligned).mean(axis=1)
    return distance.sort_values(), common_bets.tolist()

def analyze_fixture(fixture_id: int):
    """Main analysis workflow for a single fixture with enhanced diagnostics."""
    logging.info(f"--- Starting Analysis for Fixture ID: {fixture_id} ---")
    output_dir, output_path = 'analysis/predictions', os.path.join('analysis/predictions', f"prediction_{fixture_id}.json")
    os.makedirs(output_dir, exist_ok=True)

    report = {'fixture_id': fixture_id, 'prediction_timestamp': datetime.now().isoformat(), 'status': 'failed', 'diagnostics': {}}

    try:
        historical_df = pd.read_parquet(config.PROCESSED_DATA_PATH)
        target_odds_vector = get_api_odds_for_fixture(fixture_id)

        if target_odds_vector.empty:
            raise ValueError("Could not retrieve or process odds for the target fixture.")

        target_vector = target_odds_vector.iloc[0]
        historical_matrix = historical_df.drop(columns=['result', 'home_team_name', 'away_team_name'], errors='ignore')

        all_distances, common_bets = find_similar_matches(target_vector, historical_matrix)

        report['diagnostics'] = {
            'common_bets_count': len(common_bets),
            'distance_stats': all_distances.describe().to_dict() if not all_distances.empty else None
        }

        if all_distances.empty:
            raise ValueError("Could not calculate distances, likely due to no common bets.")

        similar_matches = all_distances[all_distances < config.SIMILARITY_THRESHOLD]

        if similar_matches.empty:
            report.update({'status': 'success', 'error_message': 'No historically similar matches found.'})
        else:
            results_of_similar = historical_df.loc[similar_matches.index]['result']
            report.update({
                'status': 'success',
                'similar_matches_count': len(similar_matches),
                'avg_similarity_score': similar_matches.mean(),
                'probabilities': {k: v * 100 for k, v in results_of_similar.value_counts(normalize=True).to_dict()}
            })

    except Exception as e:
        logging.error(f"Analysis for fixture {fixture_id} failed: {e}")
        report['error_message'] = str(e)

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=4)
    logging.info(f"Analysis report for fixture {fixture_id} saved to {output_path}")

    # Also print the full report to stdout for debugging in workflow logs
    print("\n--- JSON DIAGNOSTIC REPORT ---")
    print(json.dumps(report, indent=4))
    print("--------------------------\n")

def main():
    """Main entry point for preprocessing or analysis."""
    parser = argparse.ArgumentParser(description="Football Match Odds Analyzer.")
    parser.add_argument('--preprocess', action='store_true', help="Run data preprocessing.")
    parser.add_argument('--analyze', type=int, metavar='FIXTURE_ID', help="Analyze a specific fixture ID.")
    args = parser.parse_args()

    if args.preprocess:
        preprocess_and_save_data()
    elif args.analyze:
        analyze_fixture(args.analyze)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
