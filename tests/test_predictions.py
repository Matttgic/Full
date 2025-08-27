import pytest
import pandas as pd
import numpy as np
import requests
from src.prediction.daily_predictions_workflow import DailyPredictionsWorkflow
from src.config import (
    SIMILARITY_THRESHOLD,
    MIN_BOOKMAKERS_THRESHOLD,
    MIN_SIMILAR_MATCHES_THRESHOLD,
    MIN_SIMILARITY_PCT_THRESHOLD
)

@pytest.fixture
def predictions_workflow(mocker):
    """
    Fixture pour initialiser DailyPredictionsWorkflow avec des dépendances mockées.
    """
    mocker.patch.object(DailyPredictionsWorkflow, 'load_all_historical_odds', return_value=pd.DataFrame())
    mocker.patch.object(DailyPredictionsWorkflow, 'create_comprehensive_feature_matrix', return_value=pd.DataFrame())
    workflow = DailyPredictionsWorkflow(rapidapi_key='dummy_key_for_testing')
    return workflow

def test_process_fixture_odds_filters_bookmakers(predictions_workflow):
    """Vérifie que les paris avec trop peu de bookmakers sont exclus."""
    odds_data = [{
        'bookmakers': [
            {'id': 1, 'bets': [{'name': 'Match Winner', 'values': [{'value': 'Home', 'odd': '1.5'}]}]},
            {'id': 2, 'bets': [{'name': 'Match Winner', 'values': [{'value': 'Home', 'odd': '1.6'}]}]},
            {'id': 3, 'bets': [{'name': 'Match Winner', 'values': [{'value': 'Home', 'odd': '1.7'}]}]},
            {'id': 4, 'bets': [{'name': 'Over/Under', 'values': [{'value': 'Over 2.5', 'odd': '2.0'}]}]},
            {'id': 5, 'bets': [{'name': 'Over/Under', 'values': [{'value': 'Over 2.5', 'odd': '2.1'}]}]},
        ]
    }]

    result = predictions_workflow.process_fixture_odds(1, odds_data)

    assert 'Match Winner_Home' in result
    assert result['Match Winner_Home'] == pytest.approx((1.5 + 1.6 + 1.7) / 3)
    assert 'Over/Under_Over 2.5' not in result

def test_calculate_similarity_with_all_thresholds(predictions_workflow):
    """
    Teste que les deux seuils (`MIN_SIMILAR_MATCHES_THRESHOLD` et
    `MIN_SIMILARITY_PCT_THRESHOLD`) sont correctement appliqués.
    """
    # 1. Préparation des données de test

    # Cas 1: Doit passer tous les filtres
    # 12 matchs similaires sur 15 au total -> 80% de similarité
    data_pass = [1.50] * 12 + [2.0] * 3

    # Cas 2: Doit échouer car pas assez de matchs similaires au total
    data_fail_count = [1.80] * 8 # Moins de 10

    # Cas 3: Doit échouer car le % de similarité est trop bas
    # 12 matchs similaires sur 20 au total -> 60% de similarité
    data_fail_pct = [2.20] * 12 + [3.0] * 8

    # Assurer que les listes ont la même longueur pour le DataFrame
    max_len = max(len(data_pass), len(data_fail_count), len(data_fail_pct))
    data_pass.extend([np.nan] * (max_len - len(data_pass)))
    data_fail_count.extend([np.nan] * (max_len - len(data_fail_count)))
    data_fail_pct.extend([np.nan] * (max_len - len(data_fail_pct)))

    historical_data = {
        'Pass_Bet': data_pass,
        'Fail_Count_Bet': data_fail_count,
        'Fail_Pct_Bet': data_fail_pct
    }
    historical_matrix = pd.DataFrame(historical_data)
    predictions_workflow.historical_feature_matrix = historical_matrix

    # Cotes cibles
    target_odds = {
        'Pass_Bet': 1.52,
        'Fail_Count_Bet': 1.81,
        'Fail_Pct_Bet': 2.22
    }

    # Utiliser les seuils de la configuration
    predictions_workflow.SIMILARITY_THRESHOLD = 0.1 # Pour un test prédictible
    predictions_workflow.MIN_SIMILAR_MATCHES_THRESHOLD = 10
    predictions_workflow.MIN_SIMILARITY_PCT_THRESHOLD = 70

    # 2. Exécution
    similarity_results = predictions_workflow.calculate_similarity_for_all_bets(target_odds)

    # 3. Vérification

    # Le pari 'Pass_Bet' doit être présent
    assert 'Pass_Bet' in similarity_results
    assert similarity_results['Pass_Bet']['similar_matches_count'] == 12
    assert similarity_results['Pass_Bet']['similarity_percentage'] == 80.0
    assert similarity_results['Pass_Bet']['similarity_reference_count'] == 15

    # Les autres paris doivent avoir été filtrés
    assert 'Fail_Count_Bet' not in similarity_results
    assert 'Fail_Pct_Bet' not in similarity_results


def test_make_api_request_success(predictions_workflow, mocker):
    """Vérifie qu'une réponse API valide est renvoyée correctement."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "ok"}
    mocker.patch("requests.get", return_value=mock_response)

    data = predictions_workflow.make_api_request("fixtures", {"a": 1})

    assert data == {"response": "ok"}


def test_make_api_request_failure(predictions_workflow, mocker):
    """Vérifie que la fonction renvoie None après des erreurs répétées."""
    mock_get = mocker.patch(
        "requests.get", side_effect=requests.exceptions.RequestException("boom")
    )
    mocker.patch("src.prediction.daily_predictions_workflow.time.sleep", return_value=None)

    data = predictions_workflow.make_api_request("fixtures", {"a": 1})

    assert data is None
    assert mock_get.call_count == 3


def test_get_fixture_odds_calls_api(predictions_workflow, mocker):
    """Vérifie que get_fixture_odds utilise make_api_request."""
    mocker.patch.object(
        predictions_workflow,
        "make_api_request",
        return_value={"response": ["sample"]},
    )

    result = predictions_workflow.get_fixture_odds(123)

    predictions_workflow.make_api_request.assert_called_once_with(
        "odds", {"fixture": 123}
    )
    assert result == ["sample"]


def test_create_daily_predictions_csv_exports_counts(predictions_workflow, mocker, tmp_path):
    """Vérifie que le CSV quotidien contient les compteurs de similarité."""
    predictions_workflow.predictions_dir = str(tmp_path)

    fixtures_data = [{
        'fixture': {
            'id': 1,
            'date': '2024-01-01T00:00:00+00:00',
            'venue': {'name': 'Test Venue'},
            'status': {'long': 'NS'}
        },
        'teams': {
            'home': {'name': 'Home'},
            'away': {'name': 'Away'}
        },
        'league': {'name': 'League'},
        'league_code': 'LC',
        'country': 'Country'
    }]

    mocker.patch.object(predictions_workflow, 'get_fixture_odds', return_value=[{}])
    mocker.patch.object(predictions_workflow, 'process_fixture_odds', return_value={'Bet_X_value': 1.5})
    mocker.patch.object(
        predictions_workflow,
        'calculate_similarity_for_all_bets',
        return_value={
            'Bet_X_value': {
                'similarity_percentage': 80.0,
                'similar_matches_count': 12,
                'total_historical_matches': 15,
                'avg_distance': 0.1,
                'target_odd': 1.5,
                'similarity_reference_count': 15
            }
        }
    )

    daily_file, _ = predictions_workflow.create_daily_predictions_csv(fixtures_data)
    df = pd.read_csv(daily_file)

    assert 'similar_matches_count' in df.columns
    assert 'similarity_reference_count' in df.columns
    assert df.loc[0, 'similar_matches_count'] == 12
    assert df.loc[0, 'similarity_reference_count'] == 15
