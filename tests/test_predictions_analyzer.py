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

