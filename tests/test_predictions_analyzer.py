import os
import pandas as pd
from src.analysis.predictions_analyzer import PredictionsAnalyzer


def test_load_historical_data(tmp_path):
    """Test le chargement des données historiques."""
    predictions_dir = tmp_path / "data/predictions"
    predictions_dir.mkdir(parents=True)
    file_path = predictions_dir / "historical_predictions.csv"
    pd.DataFrame({
        "fixture_id": [1, 2],
        "league_name": ["A", "B"],
        "total_bet_types_analyzed": [3, 4],
    }).to_csv(file_path, index=False)

    analyzer = PredictionsAnalyzer()
    analyzer.predictions_dir = str(predictions_dir)
    analyzer.historical_file = str(file_path)

    df = analyzer.load_historical_data()
    assert not df.empty
    assert len(df) == 2


def test_analyze_by_league():
    """Test l'analyse par ligue."""
    analyzer = PredictionsAnalyzer()
    df = pd.DataFrame({
        "fixture_id": [1, 2, 3],
        "league_name": ["L1", "L1", "L2"],
        "total_bet_types_analyzed": [2, 4, 6],
    })

    result = analyzer.analyze_by_league(df)
    assert result.loc["L1", "matches_analyzed"] == 2
    assert result.loc["L1", "avg_bet_types_per_match"] == 3


def test_export_filtered_data(tmp_path):
    """Test l'export de données filtrées."""
    analyzer = PredictionsAnalyzer()
    analyzer.predictions_dir = str(tmp_path)
    df = pd.DataFrame({
        "date": ["2025-01-01", "2025-02-01"],
        "league_name": ["A", "B"],
        "fixture_id": [1, 2],
        "total_bet_types_analyzed": [3, 4],
    })

    output = analyzer.export_filtered_data(df, {"league": ["B"]})
    assert os.path.exists(output)
    saved = pd.read_csv(output)
    assert saved["league_name"].unique().tolist() == ["B"]


def test_compute_bet_success_rates_match_winner():
    analyzer = PredictionsAnalyzer()
    df = pd.DataFrame({
        "bet_type": ["Match Winner", "Match Winner", "Match Winner", "Match Winner"],
        "bet_value": ["Home", "Home", "Away", "Draw"],
        "home_goals_fulltime": [2, 0, 0, 1],
        "away_goals_fulltime": [1, 1, 2, 1],
    })

    summary = analyzer.compute_bet_success_rates(df)
    home_row = summary[(summary["bet_type"] == "Match Winner") & (summary["bet_value"] == "Home")].iloc[0]
    assert home_row["total_bets"] == 2
    assert home_row["successes"] == 1
    assert home_row["success_rate"] == 0.5


def test_compute_bet_success_rates_btts():
    analyzer = PredictionsAnalyzer()
    df = pd.DataFrame({
        "bet_type": ["Both Teams Score", "Both Teams Score", "Both Teams Score", "Both Teams Score"],
        "bet_value": ["Yes", "Yes", "No", "No"],
        "home_goals_fulltime": [1, 0, 2, 2],
        "away_goals_fulltime": [1, 1, 0, 2],
    })

    summary = analyzer.compute_bet_success_rates(df)
    yes_row = summary[(summary["bet_type"] == "Both Teams Score") & (summary["bet_value"] == "Yes")].iloc[0]
    assert yes_row["total_bets"] == 2
    assert yes_row["successes"] == 1
    assert yes_row["success_rate"] == 0.5


def test_compute_bet_success_rates_over_under():
    analyzer = PredictionsAnalyzer()
    df = pd.DataFrame({
        "bet_type": [
            "Goals Over/Under",
            "Goals Over/Under",
            "Goals Over/Under",
            "Goals Over/Under",
        ],
        "bet_value": [
            "Over 2.5",
            "Over 2.5",
            "Under 3.5",
            "Under 1.5",
        ],
        "home_goals_fulltime": [2, 1, 1, 2],
        "away_goals_fulltime": [1, 1, 1, 0],
    })

    summary = analyzer.compute_bet_success_rates(df)
    over_row = summary[(summary["bet_type"] == "Goals Over/Under") & (summary["bet_value"] == "Over 2.5")].iloc[0]
    assert over_row["total_bets"] == 2
    assert over_row["successes"] == 1
    assert over_row["success_rate"] == 0.5
    under_row = summary[(summary["bet_type"] == "Goals Over/Under") & (summary["bet_value"] == "Under 3.5")].iloc[0]
    assert under_row["total_bets"] == 1
    assert under_row["successes"] == 1
    assert under_row["success_rate"] == 1.0

