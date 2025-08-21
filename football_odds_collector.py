import requests
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import logging
import argparse
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

def setup_logging(league_code: Optional[str] = None):
    """Configure le logging pour écrire dans un fichier spécifique à la ligue."""
    log_file = f"football_odds_maintenance_{league_code}.log" if league_code else "football_odds_maintenance.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
        force=True # Permet de reconfigurer le logging si nécessaire
    )
    logger.info(f"Logging configuré pour écrire dans {log_file}")

class FootballOddsMaintainer:
    """
    Maintient une base de données de cotes de football sur une fenêtre glissante de 365 jours.
    - Supprime les cotes de plus de 365 jours.
    - Récupère les cotes pour les matchs de la semaine écoulée.
    """

    def __init__(self, rapidapi_key: str):
        """
        Initialise le mainteneur avec la clé RapidAPI.
        """
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }

        self.all_leagues = {
            'ENG1': {'id': 39, 'name': 'Premier League', 'country': 'England'},
            'FRA1': {'id': 61, 'name': 'Ligue 1', 'country': 'France'},
            'ITA1': {'id': 135, 'name': 'Serie A', 'country': 'Italy'},
            'GER1': {'id': 78, 'name': 'Bundesliga', 'country': 'Germany'},
            'SPA1': {'id': 140, 'name': 'La Liga', 'country': 'Spain'},
            'NED1': {'id': 88, 'name': 'Eredivisie', 'country': 'Netherlands'},
            'POR1': {'id': 94, 'name': 'Primeira Liga', 'country': 'Portugal'},
            'BEL1': {'id': 144, 'name': 'Jupiler Pro League', 'country': 'Belgium'},
            'ENG2': {'id': 40, 'name': 'Championship', 'country': 'England'},
            'FRA2': {'id': 62, 'name': 'Ligue 2', 'country': 'France'},
            'ITA2': {'id': 136, 'name': 'Serie B', 'country': 'Italy'},
            'GER2': {'id': 79, 'name': '2. Bundesliga', 'country': 'Germany'},
            'SPA2': {'id': 141, 'name': 'Segunda División', 'country': 'Spain'},
            'TUR1': {'id': 203, 'name': 'Süper Lig', 'country': 'Turkey'},
            'SAU1': {'id': 307, 'name': 'Saudi Pro League', 'country': 'Saudi Arabia'}
        }

        # Fenêtre de temps pour la collecte : 7 jours passés
        self.collection_end_date = datetime.now().date()
        self.collection_start_date = (self.collection_end_date - timedelta(days=7))

        # Date limite pour la suppression : tout ce qui est plus vieux que 365 jours
        self.prune_cutoff_date = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=365)


        self.matches_folder = os.path.join("data", "matches")
        self.odds_folder = os.path.join("data", "odds", "raw_data")
        os.makedirs(self.odds_folder, exist_ok=True)

        self.stats = {
            'leagues_processed': set(),
            'records_before_prune': 0,
            'records_after_prune': 0,
            'new_fixtures_found': 0,
            'new_odds_collections': 0
        }

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API avec gestion des erreurs et des retries."""
        url = f"{self.base_url}/{endpoint}"
        for _ in range(3):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API {response.status_code}: {response.text[:200]}")
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur de requête: {e}")
                time.sleep(5)
        return None

    def get_fixture_odds(self, fixture_id: int) -> Optional[List[Dict]]:
        """Récupère les cotes pour un match spécifique."""
        logger.info(f"🔍 Appel API pour les cotes du match {fixture_id}")
        params = {'fixture': fixture_id}
        data = self.make_api_request('odds', params)
        return data['response'] if data and 'response' in data else None

    def process_odds_data(self, fixture_id: int, odds_data: List[Dict]) -> List[Dict]:
        """Traite les données de cotes brutes pour les transformer en une liste de dictionnaires."""
        processed_odds = []
        if not odds_data:
            return processed_odds
        for odds_entry in odds_data:
            for bookmaker in odds_entry.get('bookmakers', []):
                for bet in bookmaker.get('bets', []):
                    for value in bet.get('values', []):
                        processed_odds.append({
                            'fixture_id': fixture_id,
                            'fixture_date': odds_entry.get('fixture', {}).get('date'),
                            'bookmaker_id': bookmaker.get('id'),
                            'bookmaker_name': bookmaker.get('name'),
                            'bet_type_id': bet.get('id'),
                            'bet_type_name': bet.get('name'),
                            'bet_value': value.get('value'),
                            'odd': value.get('odd'),
                            'collected_at': datetime.now().isoformat()
                        })
        if processed_odds:
            self.stats['new_odds_collections'] += 1
        return processed_odds

    def get_fixtures_to_collect(self, league_code: str) -> pd.DataFrame:
        """Charge les matchs d'une ligue et les filtre pour la fenêtre de collecte."""
        match_file = os.path.join(self.matches_folder, f"{league_code}.csv")
        if not os.path.exists(match_file):
            logger.warning(f"Fichier de matchs manquant pour {league_code}: {match_file}")
            return pd.DataFrame()

        df = pd.read_csv(match_file)
        df['date'] = pd.to_datetime(df['date'])

        mask = (df['date'] >= self.collection_start_date) & (df['date'] <= self.collection_end_date)
        return df[mask].copy()

    def process_league(self, league_code: str):
        """
        Traite une seule ligue : supprime les anciennes données, collecte les nouvelles.
        """
        logger.info(f"--- Traitement de la ligue : {league_code} ---")
        odds_file_path = os.path.join(self.odds_folder, f"{league_code}_complete_odds.csv")
        cols = ['fixture_id', 'fixture_date', 'bookmaker_id', 'bookmaker_name', 'bet_type_id', 'bet_type_name', 'bet_value', 'odd', 'collected_at']

        # 1. Charger les données existantes
        odds_df = pd.read_csv(odds_file_path) if os.path.exists(odds_file_path) else pd.DataFrame(columns=cols)
        if not odds_df.empty:
            odds_df['fixture_date'] = pd.to_datetime(odds_df['fixture_date'])

        self.stats['records_before_prune'] = len(odds_df)

        # 2. Supprimer les données de plus de 365 jours
        if not odds_df.empty:
            odds_df = odds_df[odds_df['fixture_date'] >= self.prune_cutoff_date]
            self.stats['records_after_prune'] = len(odds_df)
            logger.info(f"[{league_code}] Suppression : {self.stats['records_before_prune'] - self.stats['records_after_prune']} enregistrements anciens supprimés.")

        # 3. Collecter les nouvelles données pour la semaine passée
        fixtures_to_check = self.get_fixtures_to_collect(league_code)
        new_odds_data = []
        if not fixtures_to_check.empty:
            existing_fixture_ids = set(odds_df['fixture_id'].unique())
            fixtures_to_process = fixtures_to_check[~fixtures_to_check['fixture_id'].isin(existing_fixture_ids)]
            self.stats['new_fixtures_found'] = len(fixtures_to_process)
            logger.info(f"[{league_code}] Collecte : {self.stats['new_fixtures_found']} nouveaux matchs à traiter.")

            for _, fixture in fixtures_to_process.iterrows():
                odds_data = self.get_fixture_odds(fixture['fixture_id'])
                if odds_data:
                    new_odds_data.extend(self.process_odds_data(fixture['fixture_id'], odds_data))
                time.sleep(1.5)

        # 4. Combiner et sauvegarder
        if new_odds_data:
            new_odds_df = pd.DataFrame(new_odds_data)
            combined_df = pd.concat([odds_df, new_odds_df]).reset_index(drop=True)
            # Dédoublonner
            key_cols = ['fixture_id', 'bookmaker_id', 'bet_type_id', 'bet_value']
            combined_df.drop_duplicates(subset=key_cols, keep='last', inplace=True)
        else:
            combined_df = odds_df
            logger.info(f"[{league_code}] Aucune nouvelle cote à ajouter.")

        combined_df.to_csv(odds_file_path, index=False, encoding='utf-8')
        logger.info(f"💾 Fichier de cotes pour {league_code} sauvegardé avec {len(combined_df)} lignes.")
        self.stats['leagues_processed'].add(league_code)

    def run_maintenance(self, league_to_process: Optional[str] = None):
        """Lance le processus de maintenance pour une ou toutes les ligues."""
        logger.info("🚀 === DÉBUT DE LA MAINTENANCE DES COTES ===")
        leagues_to_run = [league_to_process] if league_to_process else list(self.all_leagues.keys())

        for league_code in leagues_to_run:
            try:
                self.process_league(league_code)
                if len(leagues_to_run) > 1:
                    time.sleep(5)
            except Exception as e:
                logger.error(f"❌ Erreur majeure lors du traitement de {league_code}: {e}", exc_info=True)

        logger.info("\n🎉 === MAINTENANCE TERMINÉE ===")

def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(description="Mainteneur de cotes de football.")
    parser.add_argument("--league", type=str, help="Code de la ligue à traiter (ex: ENG1).")
    args = parser.parse_args()

    # Configurer le logging après avoir parsé les arguments
    setup_logging(args.league)

    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée.")
        return

    maintainer = FootballOddsMaintainer(RAPIDAPI_KEY)
    maintainer.run_maintenance(league_to_process=args.league)

if __name__ == "__main__":
    main()
