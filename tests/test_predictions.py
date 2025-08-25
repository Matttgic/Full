import pytest
import pandas as pd
import numpy as np
from src.prediction.daily_predictions_workflow import DailyPredictionsWorkflow
from src.config import SIMILARITY_THRESHOLD, MIN_BOOKMAKERS_THRESHOLD, MIN_SIMILAR_MATCHES_THRESHOLD

@pytest.fixture
def predictions_workflow(mocker):
    """
    Fixture pour initialiser DailyPredictionsWorkflow avec des dépendances mockées.
    """
    mocker.patch.object(DailyPredictionsWorkflow, 'load_all_historical_odds', return_value=pd.DataFrame())
    mocker.patch.object(DailyPredictionsWorkflow, 'create_comprehensive_feature_matrix', return_value=pd.DataFrame())
    workflow = DailyPredictionsWorkflow(rapidapi_key='dummy_key_for_testing')
    return workflow

def test_calculate_similarity_with_thresholds(predictions_workflow):
    """
    Teste que le `MIN_SIMILAR_MATCHES_THRESHOLD` est correctement appliqué.
    """
    # 1. Préparation des données de test

    # Données pour la matrice historique factice
    # On s'assure que les cotes pour 'Match Winner_Home' sont dans la plage de similarité
    data_winner = [1.50, 1.52, 1.48, 1.55, 1.45, 1.58, 1.60, 1.49, 1.51, 1.53, 1.56]  # 11 matchs
    # Données pour 'Correct Score_1-0' qui n'atteindront pas le seuil
    data_score = [8.0, 8.2, 7.8, 8.1, 7.9]  # 5 matchs

    # Assurer que les listes ont la même longueur pour le DataFrame
    max_len = max(len(data_winner), len(data_score))
    data_winner.extend([np.nan] * (max_len - len(data_winner)))
    data_score.extend([np.nan] * (max_len - len(data_score)))

    historical_data = {
        'Match Winner_Home': data_winner,
        'Correct Score_1-0': data_score
    }
    historical_matrix = pd.DataFrame(historical_data)
    predictions_workflow.historical_feature_matrix = historical_matrix

    # Cotes cibles pour un nouveau match
    target_odds = {
        'Match Winner_Home': 1.52,
        'Correct Score_1-0': 8.05
    }

    # Utiliser les seuils de la configuration
    predictions_workflow.SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLD
    predictions_workflow.MIN_SIMILAR_MATCHES_THRESHOLD = MIN_SIMILAR_MATCHES_THRESHOLD # Devrait être 10

    # 2. Exécution de la méthode à tester
    similarity_results = predictions_workflow.calculate_similarity_for_all_bets(target_odds)

    # 3. Vérification des résultats

    # Le pari 'Match Winner_Home' doit être présent car il a 11 matchs similaires
    # (1.52 +/- 0.15 -> [1.37, 1.67]), ce qui est > 10.
    assert 'Match Winner_Home' in similarity_results
    assert similarity_results['Match Winner_Home']['similar_matches_count'] == 11

    # Le pari 'Correct Score_1-0' ne doit pas être présent car il n'a que 5 matchs similaires,
    # ce qui est < 10.
    assert 'Correct Score_1-0' not in similarity_results
