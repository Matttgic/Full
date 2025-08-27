import pandas as pd
import os


def create_daily_elo_csv(
    input_path: str = "data/predictions/daily_elo_predictions.csv",
    output_path: str = "todays_leagues_elo.csv",
):
    """Create a CSV with only league matches from daily Elo predictions.

    Parameters
    ----------
    input_path:
        Path to the CSV containing the daily Elo predictions.
    output_path:
        Destination path for the filtered league matches.
    """
    try:
        daily_predictions_df = pd.read_csv(input_path)

        # Filter out cup matches, keeping only league matches.
        # We assume anything with "Cup" in the name is a cup match.
        league_matches_df = daily_predictions_df[
            ~daily_predictions_df["league_name"].str.contains("Cup", case=False, na=False)
        ]

        league_matches_df.to_csv(output_path, index=False)
        print(f"Successfully created {output_path}")

    except FileNotFoundError:
        print(f"Error: {input_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_historical_matches_csv(
    matches_dir: str = "data/matches", output_path: str = "historical_matches.csv"
):
    """Combine all historical match data into a single CSV file.

    Parameters
    ----------
    matches_dir:
        Directory containing match CSV files.
    output_path:
        Destination path for the combined CSV.
    """
    try:
        if not os.path.isdir(matches_dir):
            print(f"Error: Directory '{matches_dir}' not found.")
            return

        all_matches_files = [
            os.path.join(matches_dir, f) for f in os.listdir(matches_dir) if f.endswith(".csv")
        ]

        if not all_matches_files:
            print(f"No CSV files found in '{matches_dir}'.")
            return

        df_list = [pd.read_csv(file) for file in all_matches_files]
        combined_df = pd.concat(df_list, ignore_index=True)

        combined_df.to_csv(output_path, index=False)
        print(f"Successfully created {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_daily_elo_csv()
    create_historical_matches_csv()
