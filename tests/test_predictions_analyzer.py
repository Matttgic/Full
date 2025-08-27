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
    df = pd.DataFrame([
        {
            'bet_type': 'Match Winner',
            'bet_value': 'Home',
            'home_goals_fulltime': 2,
            'away_goals_fulltime': 1
        },
        {
            'bet_type': 'Match Winner',
            'bet_value': 'Away',
            'home_goals_fulltime': 0,
            'away_goals_fulltime': 1
        },
        {
            'bet_type': 'Match Winner',
            'bet_value': 'Away',
            'home_goals_fulltime': 3,
            'away_goals_fulltime': 1
        },
    ])

    result = analyzer.compute_bet_success_rates(df)

    home = result[(result['bet_type'] == 'Match Winner') & (result['bet_value'] == 'Home')].iloc[0]
    away = result[(result['bet_type'] == 'Match Winner') & (result['bet_value'] == 'Away')].iloc[0]

    assert home['total_bets'] == 1 and home['successes'] == 1
    assert away['total_bets'] == 2 and away['successes'] == 1 and away['success_rate'] == 50.0


def test_compute_bet_success_rates_goals_over_under():
    analyzer = PredictionsAnalyzer()
    df = pd.DataFrame([
        {
            'bet_type': 'Goals Over/Under',
            'bet_value': 'Over 2.5',
            'home_goals_fulltime': 2,
            'away_goals_fulltime': 1
        },
        {
            'bet_type': 'Goals Over/Under',
            'bet_value': 'Under 1.5',
            'home_goals_fulltime': 1,
            'away_goals_fulltime': 0
        },
        {
            'bet_type': 'Goals Over/Under',
            'bet_value': 'Over 3.5',
            'home_goals_fulltime': 1,
            'away_goals_fulltime': 1
        },
    ])

    result = analyzer.compute_bet_success_rates(df)

    over = result[(result['bet_type'] == 'Goals Over/Under') & (result['bet_value'] == 'Over 2.5')].iloc[0]
    under = result[(result['bet_type'] == 'Goals Over/Under') & (result['bet_value'] == 'Under 1.5')].iloc[0]

    assert over['successes'] == 1 and over['success_rate'] == 100.0
    assert under['successes'] == 1 and under['success_rate'] == 100.0


def test_compute_bet_success_rates_both_teams_score():
    analyzer = PredictionsAnalyzer()
    df = pd.DataFrame([
        {
            'bet_type': 'Both Teams Score',
            'bet_value': 'Yes',
            'home_goals_fulltime': 1,
            'away_goals_fulltime': 1
        },
        {
            'bet_type': 'Both Teams Score',
            'bet_value': 'Yes',
            'home_goals_fulltime': 2,
            'away_goals_fulltime': 0
        },
        {
            'bet_type': 'Both Teams Score',
            'bet_value': 'No',
            'home_goals_fulltime': 0,
            'away_goals_fulltime': 0
        },
    ])

    result = analyzer.compute_bet_success_rates(df)

    yes = result[(result['bet_type'] == 'Both Teams Score') & (result['bet_value'] == 'Yes')].iloc[0]
    no = result[(result['bet_type'] == 'Both Teams Score') & (result['bet_value'] == 'No')].iloc[0]

    assert yes['total_bets'] == 2 and yes['successes'] == 1 and yes['success_rate'] == 50.0
    assert no['total_bets'] == 1 and no['successes'] == 1 and no['success_rate'] == 100.0

