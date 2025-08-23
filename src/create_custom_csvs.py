import pandas as pd
import os

def create_daily_elo_csv():
    """
    Reads the daily Elo predictions, filters out cup matches,
    and saves the result to a new CSV file.
    """
    try:
        daily_predictions_df = pd.read_csv('data/predictions/daily_elo_predictions_2025-08-23.csv')

        # Filter out cup matches, keeping only league matches
        # We assume anything with "Cup" in the name is a cup match.
        league_matches_df = daily_predictions_df[~daily_predictions_df['league_name'].str.contains("Cup", case=False, na=False)]

        output_path = 'todays_leagues_elo.csv'
        league_matches_df.to_csv(output_path, index=False)
        print(f"Successfully created {output_path}")

    except FileNotFoundError:
        print("Error: data/predictions/daily_elo_predictions_2025-08-23.csv not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_historical_matches_csv():
    """
    Combines all historical match data from the data/matches
    directory into a single CSV file.
    """
    matches_dir = 'data/matches'
    try:
        if not os.path.isdir(matches_dir):
            print(f"Error: Directory '{matches_dir}' not found.")
            return

        all_matches_files = [os.path.join(matches_dir, f) for f in os.listdir(matches_dir) if f.endswith('.csv')]

        if not all_matches_files:
            print(f"No CSV files found in '{matches_dir}'.")
            return

        df_list = [pd.read_csv(file) for file in all_matches_files]
        combined_df = pd.concat(df_list, ignore_index=True)

        output_path = 'historical_matches.csv'
        combined_df.to_csv(output_path, index=False)
        print(f"Successfully created {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_daily_elo_csv()
    create_historical_matches_csv()
