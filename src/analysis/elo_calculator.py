"""
Ce script est responsable du calcul des classements Elo pour les équipes de football.

Rôle :
- Parcourt tous les fichiers de matchs disponibles dans `data/matches/`.
- Calcule et met à jour le score Elo de chaque équipe après chaque match.
- Gère un système d'Elo initial différencié par ligue pour une meilleure précision
  (par exemple, une équipe de Ligue 1 commence avec un Elo plus élevé qu'une équipe de Ligue 2).
- Sauvegarde les classements Elo finaux dans `data/elo_ratings.csv`.

Pour exécuter ce script :
python3 src/analysis/elo_calculator.py
"""
import pandas as pd
import numpy as np
import os
import glob
import logging
from typing import Dict

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ajout d'un dictionnaire pour l'Elo initial par ligue
LEAGUE_INITIAL_ELO = {
    "FRA1": 1500, "ENG1": 1500, "SPA1": 1500, "ITA1": 1500, "GER1": 1500, "POR1": 1450, "NED1": 1450, "BEL1": 1400, "TUR1": 1400, "SAU1": 1300,
    "FRA2": 1350, "ENG2": 1350, "SPA2": 1350, "ITA2": 1350, "GER2": 1350,
}

class EloCalculator:
    """
    Calcule le classement Elo pour les équipes de football.
    """

    def __init__(self, k_factor: int = 40, initial_elo: int = 1500, league_initial_elos: Dict[str, int] = None):
        """
        Initialise le calculateur Elo.

        :param k_factor: Le facteur K, qui détermine l'impact du résultat d'un match.
        :param initial_elo: Le score Elo de départ par défaut pour toute nouvelle équipe.
        :param league_initial_elos: Un dictionnaire mappant les ligues à leur Elo de départ.
        """
        self.k_factor = k_factor
        self.initial_elo = initial_elo
        self.league_initial_elos = league_initial_elos or {}
        self.elo_ratings = {}  # Stocke les scores Elo actuels: {league: {team_name: elo}}

    def get_elo(self, league: str, team: str) -> int:
        """Récupère le score Elo d'une équipe, ou l'initialise si elle est nouvelle."""
        if league not in self.elo_ratings:
            self.elo_ratings[league] = {}

        # Utilise l'Elo spécifique à la ligue, ou la valeur par défaut
        initial_elo_for_league = self.league_initial_elos.get(league, self.initial_elo)
        return self.elo_ratings[league].get(team, initial_elo_for_league)

    def update_elo(self, league: str, home_team: str, away_team: str, home_goals: int, away_goals: int):
        """Met à jour les scores Elo de deux équipes après un match."""
        home_elo = self.get_elo(league, home_team)
        away_elo = self.get_elo(league, away_team)

        # Calcul de l'espérance de victoire
        expected_home = 1 / (1 + 10**((away_elo - home_elo) / 400))
        expected_away = 1 - expected_home

        # Détermination du résultat du match (1 pour victoire, 0.5 pour nul, 0 pour défaite)
        if home_goals > away_goals:
            score_home = 1.0
        elif home_goals < away_goals:
            score_home = 0.0
        else:
            score_home = 0.5

        score_away = 1 - score_home

        # Mise à jour des scores Elo
        new_home_elo = home_elo + self.k_factor * (score_home - expected_home)
        new_away_elo = away_elo + self.k_factor * (score_away - expected_away)

        self.elo_ratings[league][home_team] = new_home_elo
        self.elo_ratings[league][away_team] = new_away_elo

    def process_league_matches(self, matches_df: pd.DataFrame, league_name: str):
        """Traite tous les matchs d'une ligue dans l'ordre chronologique."""
        if matches_df.empty:
            return

        # S'assurer que les dates sont au bon format et trier
        matches_df['date'] = pd.to_datetime(matches_df['date'])
        matches_df.sort_values('date', inplace=True)

        logger.info(f"🏆 Traitement de {len(matches_df)} matchs pour la ligue: {league_name}")

        for _, row in matches_df.iterrows():
            self.update_elo(
                league_name,
                row['home_team_name'],
                row['away_team_name'],
                row['home_goals'],
                row['away_goals']
            )

    def save_ratings_to_csv(self, output_path: str):
        """Sauvegarde les classements Elo dans un fichier CSV."""
        all_ratings = []
        for league, teams in self.elo_ratings.items():
            for team, elo in teams.items():
                all_ratings.append({
                    'league': league,
                    'team_name': team,
                    'elo_rating': round(elo)
                })

        if not all_ratings:
            logger.warning("Aucun classement Elo à sauvegarder.")
            return

        ratings_df = pd.DataFrame(all_ratings)
        ratings_df.sort_values(['league', 'elo_rating'], ascending=[True, False], inplace=True)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ratings_df.to_csv(output_path, index=False)
        logger.info(f"💾 Classements Elo sauvegardés dans: {output_path}")

def main():
    """Point d'entrée principal pour le calcul du classement Elo."""
    logger.info("🚀 === DÉBUT DU CALCUL DU CLASSEMENT ELO ===")

    match_data_dir = 'data/matches'
    output_file = 'data/elo_ratings.csv'

    all_match_files = glob.glob(os.path.join(match_data_dir, "*.csv"))
    if not all_match_files:
        logger.error(f"Aucun fichier de match trouvé dans: {match_data_dir}")
        return

    # Utilisation du dictionnaire LEAGUE_INITIAL_ELO pour le calcul
    calculator = EloCalculator(league_initial_elos=LEAGUE_INITIAL_ELO)

    for file_path in all_match_files:
        league_code = os.path.basename(file_path).replace('.csv', '')
        try:
            matches_df = pd.read_csv(file_path)
            # Utiliser le code de la ligue pour la cohérence
            calculator.process_league_matches(matches_df, league_code)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du fichier {file_path}: {e}")

    calculator.save_ratings_to_csv(output_file)

    logger.info("✅ === CALCUL DU CLASSEMENT ELO TERMINÉ ===")

if __name__ == "__main__":
    main()
