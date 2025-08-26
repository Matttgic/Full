import pytest
import pandas as pd
import numpy as np
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

    # Les autres paris doivent avoir été filtrés
    assert 'Fail_Count_Bet' not in similarity_results
    assert 'Fail_Pct_Bet' not in similarity_results
