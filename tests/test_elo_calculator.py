import pytest
from src.analysis.elo_calculator import EloCalculator

@pytest.fixture
def elo_calculator():
    """Fixture pour fournir une instance fraîche de EloCalculator pour chaque test."""
    # Tranches d'Elo spécifiques pour les tests
    league_elos = {"Ligue 1": 1600, "Ligue 2": 1400}
    return EloCalculator(k_factor=30, initial_elo=1500, league_initial_elos=league_elos)

def test_initial_elo_default(elo_calculator):
    """Vérifie qu'une nouvelle équipe dans une ligue non spécifiée reçoit l'Elo par défaut."""
    assert elo_calculator.get_elo("Bundesliga", "Bayern Munich") == 1500

def test_initial_elo_league_specific(elo_calculator):
    """Vérifie qu'une nouvelle équipe dans une ligue spécifiée reçoit l'Elo correct."""
    assert elo_calculator.get_elo("Ligue 1", "PSG") == 1600
    assert elo_calculator.get_elo("Ligue 2", "Auxerre") == 1400

def test_get_existing_elo(elo_calculator):
    """Vérifie que le score d'une équipe existante est correctement retourné."""
    elo_calculator.elo_ratings["Ligue 1"] = {"PSG": 1650}
    assert elo_calculator.get_elo("Ligue 1", "PSG") == 1650

def test_elo_update_home_win(elo_calculator):
    """Teste la mise à jour de l'Elo après une victoire à domicile."""
    home_team = "Team A"
    away_team = "Team B"
    league = "Test League"

    # Scores initiaux (par défaut 1500)
    home_elo_before = elo_calculator.get_elo(league, home_team)
    away_elo_before = elo_calculator.get_elo(league, away_team)
    assert home_elo_before == 1500
    assert away_elo_before == 1500

    # Match : Victoire à domicile
    elo_calculator.update_elo(league, home_team, away_team, home_goals=2, away_goals=0)

    home_elo_after = elo_calculator.get_elo(league, home_team)
    away_elo_after = elo_calculator.get_elo(league, away_team)

    # L'équipe à domicile devrait gagner des points, l'équipe extérieure en perdre
    assert home_elo_after > home_elo_before
    assert away_elo_after < away_elo_before
    # La somme des changements d'Elo doit être nulle
    assert (home_elo_after - home_elo_before) + (away_elo_after - away_elo_before) == pytest.approx(0)
    # Vérification du calcul exact (Espérance de 0.5 pour des Elos égaux)
    assert home_elo_after == 1500 + 30 * (1 - 0.5)
    assert away_elo_after == 1500 + 30 * (0 - 0.5)

def test_elo_update_draw(elo_calculator):
    """Teste la mise à jour de l'Elo après un match nul."""
    home_team = "Team C"
    away_team = "Team D"
    league = "Test League"

    # Scores initiaux (l'un plus fort que l'autre)
    elo_calculator.elo_ratings[league] = {"Team C": 1600, "Team D": 1400}
    home_elo_before = elo_calculator.get_elo(league, home_team)
    away_elo_before = elo_calculator.get_elo(league, away_team)

    elo_calculator.update_elo(league, home_team, away_team, home_goals=1, away_goals=1)

    home_elo_after = elo_calculator.get_elo(league, home_team)
    away_elo_after = elo_calculator.get_elo(league, away_team)

    # L'équipe la plus forte perd des points, l'équipe la plus faible en gagne
    assert home_elo_after < home_elo_before
    assert away_elo_after > away_elo_before
    assert (home_elo_after - home_elo_before) + (away_elo_after - away_elo_before) == pytest.approx(0)

def test_elo_update_away_win_underdog(elo_calculator):
    """Teste la mise à jour de l'Elo quand un outsider gagne à l'extérieur."""
    home_team = "Team E"
    away_team = "Team F"
    league = "Test League"

    # Scores initiaux (équipe à domicile plus forte)
    elo_calculator.elo_ratings[league] = {"Team E": 1650, "Team F": 1450}
    home_elo_before = elo_calculator.get_elo(league, home_team)
    away_elo_before = elo_calculator.get_elo(league, away_team)

    # Match : Victoire de l'outsider à l'extérieur
    elo_calculator.update_elo(league, home_team, away_team, home_goals=0, away_goals=1)

    home_elo_after = elo_calculator.get_elo(league, home_team)
    away_elo_after = elo_calculator.get_elo(league, away_team)

    # L'outsider devrait gagner beaucoup de points
    assert away_elo_after > away_elo_before
    assert home_elo_after < home_elo_before
    assert (away_elo_after - away_elo_before) > 15  # Gain significatif
