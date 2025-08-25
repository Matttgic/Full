"""
Ce script génère des prédictions quotidiennes pour les matchs de football
en se basant sur les classements Elo des équipes.

Rôle :
- Récupère les matchs prévus pour le jour même via l'API de football.
- Charge les classements Elo actuels depuis `data/elo_ratings.csv`.
- Pour chaque match, calcule les probabilités de victoire, de nul et de défaite
  en se basant sur la différence d'Elo entre les deux équipes.
- Inclut la différence d'Elo brute comme information supplémentaire.
- Sauvegarde les prédictions dans un fichier CSV quotidien (`daily_elo_predictions_YYYY-MM-DD.csv`)
  et les ajoute à un historique complet (`historical_elo_predictions.csv`).

Dépendances :
- `data/elo_ratings.csv` doit exister et être à jour.
- Une clé `RAPIDAPI_KEY` valide doit être configurée comme variable d'environnement.
"""
import pandas as pd
import numpy as np
import os
import requests
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

# Configuration du logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/elo_predictions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EloPredictionWorkflow:
    """
    Workflow pour générer des prédictions basées sur le classement Elo.
    """

    def __init__(self, rapidapi_key: str):
        """
        Initialise le workflow avec la clé RapidAPI.
        """
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }

        self.elo_ratings_path = 'data/elo_ratings.csv'
        self.summary_path = 'data/analysis/elo_summary.csv'
        self.predictions_dir = 'data/predictions'
        os.makedirs(self.predictions_dir, exist_ok=True)

        self.today = date.today()

        self.elo_ratings = self.load_elo_ratings()
        self.elo_summary = self.load_elo_summary()

    def load_elo_summary(self) -> pd.DataFrame:
        """Charge le fichier de synthèse de l'analyse Elo."""
        if not os.path.exists(self.summary_path):
            logger.warning(f"Fichier de synthèse non trouvé: {self.summary_path}. Les stats historiques ne seront pas ajoutées.")
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.summary_path)
            logger.info("Synthèse de l'analyse Elo chargée.")
            return df
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier de synthèse: {e}")
            return pd.DataFrame()

    def load_elo_ratings(self) -> pd.DataFrame:
        """Charge le fichier de classement Elo."""
        if not os.path.exists(self.elo_ratings_path):
            logger.error(f"Fichier de classement Elo non trouvé: {self.elo_ratings_path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.elo_ratings_path)
            logger.info(f"Classements Elo chargés: {len(df)} équipes")
            return df
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier Elo: {e}")
            return pd.DataFrame()

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de requête API: {e}")
            return None

    def get_today_fixtures(self) -> List[Dict]:
        """Récupère les matchs du jour."""
        today_str = self.today.strftime('%Y-%m-%d')
        params = {'date': today_str}
        data = self.make_api_request('fixtures', params)

        if data and 'response' in data:
            logger.info(f"Matchs du jour récupérés: {len(data['response'])}")
            return data['response']
        return []

    def calculate_elo_probabilities(self, home_elo: float, away_elo: float) -> Tuple[float, float, float]:
        """Calcule les probabilités de victoire basées sur l'Elo."""
        # Formule de probabilité Elo
        prob_home = 1 / (1 + 10**((away_elo - home_elo) / 400))
        prob_away = 1 - prob_home

        # Pour la probabilité de match nul, nous utilisons une approche simple
        # qui la dérive des probabilités de victoire. Ce n'est pas parfait
        # mais c'est un point de départ.
        # Une approche plus avancée pourrait utiliser une distribution de Poisson
        # ou un modèle statistique.
        prob_draw = 1 - abs(prob_home - prob_away)

        # Normalisation pour que la somme fasse 1
        total_prob = prob_home + prob_away + prob_draw
        prob_home /= total_prob
        prob_away /= total_prob
        prob_draw /= total_prob

        return prob_home, prob_away, prob_draw

    def run(self):
        """Exécute le workflow de prédiction Elo."""
        logger.info("🚀 Démarrage du workflow de prédiction Elo")

        if self.elo_ratings.empty:
            logger.error("Impossible de continuer sans les classements Elo.")
            return

        fixtures = self.get_today_fixtures()
        if not fixtures:
            logger.info("Aucun match à traiter aujourd'hui.")
            return

        predictions = []
        for fixture in fixtures:
            fixture_id = fixture['fixture']['id']
            league_name = fixture['league']['name']
            home_team_name = fixture['teams']['home']['name']
            away_team_name = fixture['teams']['away']['name']

            home_team_elo = self.elo_ratings[self.elo_ratings['team_name'] == home_team_name]['elo_rating'].values
            away_team_elo = self.elo_ratings[self.elo_ratings['team_name'] == away_team_name]['elo_rating'].values

            if len(home_team_elo) == 0 or len(away_team_elo) == 0:
                logger.warning(f"Classement Elo non trouvé pour le match: {home_team_name} vs {away_team_name}")
                continue

            home_elo = home_team_elo[0]
            away_elo = away_team_elo[0]

            # Calcul de la différence d'Elo
            elo_difference = home_elo - away_elo

            prob_home, prob_away, prob_draw = self.calculate_elo_probabilities(home_elo, away_elo)

            prediction_data = {
                'fixture_id': fixture_id,
                'date': self.today.strftime('%Y-%m-%d'),
                'league_name': league_name,
                'home_team': home_team_name,
                'away_team': away_team_name,
                'home_team_elo': home_elo,
                'away_team_elo': away_elo,
                'elo_difference': elo_difference,
                'home_win_probability': round(prob_home, 4),
                'away_win_probability': round(prob_away, 4),
                'draw_probability': round(prob_draw, 4),
                'home_win_odds': round(1 / prob_home, 2) if prob_home > 0 else None,
                'away_win_odds': round(1 / prob_away, 2) if prob_away > 0 else None,
                'draw_odds': round(1 / prob_draw, 2) if prob_draw > 0 else None,
            }

            # Enrichir avec les stats historiques si disponibles
            if not self.elo_summary.empty:
                # Déterminer la tranche Elo
                elo_bins = list(range(-500, 501, 100))
                elo_labels = [f"{i} à {i+99}" for i in elo_bins[:-1]]
                elo_bin = pd.cut([elo_difference], bins=elo_bins, labels=elo_labels, right=False)[0]

                # Récupérer les stats pour cette tranche
                summary_stats = self.elo_summary[self.elo_summary['elo_bin'] == elo_bin]

                if not summary_stats.empty:
                    stats = summary_stats.iloc[0]
                    prediction_data.update({
                        'hist_home_win_pct': stats.get('home_win_pct'),
                        'hist_draw_pct': stats.get('draw_pct'),
                        'hist_away_win_pct': stats.get('away_win_pct'),
                        'hist_avg_goals': stats.get('avg_total_goals'),
                        'hist_btts_pct': stats.get('btts_pct')
                    })

            predictions.append(prediction_data)

        if not predictions:
            logger.info("Aucune prédiction n'a pu être générée.")
            return

        # Sauvegarde des prédictions
        daily_df = pd.DataFrame(predictions)
        daily_filename = f"daily_elo_predictions_{self.today.strftime('%Y-%m-%d')}.csv"
        daily_filepath = os.path.join(self.predictions_dir, daily_filename)
        daily_df.to_csv(daily_filepath, index=False)
        logger.info(f"Prédictions Elo du jour sauvegardées dans: {daily_filepath}")

        # Mise à jour de l'historique
        historical_filepath = os.path.join(self.predictions_dir, 'historical_elo_predictions.csv')
        if os.path.exists(historical_filepath):
            historical_df = pd.read_csv(historical_filepath)
            combined_df = pd.concat([historical_df, daily_df], ignore_index=True)
        else:
            combined_df = daily_df

        combined_df.drop_duplicates(subset=['fixture_id'], keep='last', inplace=True)
        combined_df.to_csv(historical_filepath, index=False)
        logger.info(f"Historique des prédictions Elo mis à jour: {historical_filepath}")

        logger.info("✅ Workflow de prédiction Elo terminé.")


def main():
    """Point d'entrée principal."""
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    if not RAPIDAPI_KEY:
        logger.error("Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement.")
        return

    workflow = EloPredictionWorkflow(rapidapi_key=RAPIDAPI_KEY)
    workflow.run()

if __name__ == "__main__":
    main()
