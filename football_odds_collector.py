import requests
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import logging
import argparse
from typing import Dict, List, Optional, Set

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('football_odds_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootballOddsCollector:
    """
    Collecte les cotes de football pour les matchs des 365 derniers jours.
    Cible les matchs pour lesquels les cotes n'ont pas encore été collectées.
    """

    def __init__(self, rapidapi_key: str):
        """
        Initialise le collecteur avec la clé RapidAPI.
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

        # Fenêtre de temps pour la collecte : 365 jours passés
        self.end_date = datetime.now().date()
        self.start_date = (datetime.now() - timedelta(days=365)).date()

        self.matches_folder = os.path.join("data", "matches")
        self.odds_folder = os.path.join("data", "odds", "raw_data")
        os.makedirs(self.odds_folder, exist_ok=True)

        self.stats = {
            'total_requests': 0,
            'fixtures_processed': 0,
            'odds_requests': 0,
            'new_odds_collections': 0,
            'leagues_processed': set()
        }

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Effectue une requête à l'API avec gestion des erreurs et des retries.
        """
        url = f"{self.base_url}/{endpoint}"
        max_retries = 3
        wait_time = 5

        self.stats['total_requests'] += 1
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning(f"Rate limit atteint. Attente de {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Erreur API {response.status_code}: {response.text[:200]}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur de requête (tentative {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
        return None

    def get_fixture_odds(self, fixture_id: int) -> Optional[List[Dict]]:
        """
        Récupère les cotes pour un match spécifique.
        """
        logger.info(f"🔍 Appel API pour les cotes du match {fixture_id}")
        self.stats['odds_requests'] += 1
        params = {'fixture': fixture_id}
        data = self.make_api_request('odds', params)
        return data['response'] if data and 'response' in data else None

    def process_odds_data(self, fixture_id: int, odds_data: List[Dict]) -> List[Dict]:
        """
        Traite les données de cotes brutes pour les transformer en une liste de dictionnaires.
        """
        processed_odds = []
        if not odds_data:
            return processed_odds

        for odds_entry in odds_data:
            fixture_info = odds_entry.get('fixture', {})
            for bookmaker in odds_entry.get('bookmakers', []):
                for bet in bookmaker.get('bets', []):
                    for value in bet.get('values', []):
                        record = {
                            'fixture_id': fixture_id,
                            'fixture_date': fixture_info.get('date'),
                            'bookmaker_id': bookmaker.get('id'),
                            'bookmaker_name': bookmaker.get('name'),
                            'bet_type_id': bet.get('id'),
                            'bet_type_name': bet.get('name'),
                            'bet_value': value.get('value'),
                            'odd': value.get('odd'),
                            'collected_at': datetime.now().isoformat()
                        }
                        processed_odds.append(record)

        if processed_odds:
            self.stats['new_odds_collections'] += 1
        return processed_odds

    def get_fixtures_to_collect(self, league_code: str) -> pd.DataFrame:
        """
        Charge les matchs d'une ligue et les filtre pour la fenêtre de collecte.
        """
        match_file = os.path.join(self.matches_folder, f"{league_code}.csv")
        if not os.path.exists(match_file):
            logger.warning(f"Fichier de matchs manquant pour {league_code}: {match_file}")
            return pd.DataFrame()

        df = pd.read_csv(match_file, parse_dates=['date'])
        df['date_only'] = df['date'].dt.date

        fixtures_in_window = df[
            (df['date_only'] >= self.start_date) &
            (df['date_only'] <= self.end_date)
        ].copy()

        logger.info(f"[{league_code}] {len(df)} matchs chargés, {len(fixtures_in_window)} dans la fenêtre de collecte.")
        return fixtures_in_window

    def collect_league_odds(self, league_code: str):
        """
        Collecte les cotes pour une seule ligue et garantit la création d'un fichier.
        """
        logger.info(f"--- Collecte des cotes pour la ligue: {league_code} ---")
        odds_file_path = os.path.join(self.odds_folder, f"{league_code}_complete_odds.csv")

        cols = ['fixture_id', 'fixture_date', 'bookmaker_id', 'bookmaker_name', 'bet_type_id', 'bet_type_name', 'bet_value', 'odd', 'collected_at']
        existing_odds_df = pd.read_csv(odds_file_path) if os.path.exists(odds_file_path) else pd.DataFrame(columns=cols)

        fixtures_to_check = self.get_fixtures_to_collect(league_code)

        new_odds_data = []
        if not fixtures_to_check.empty:
            processed_fixtures = set(existing_odds_df['fixture_id'].unique())
            logger.info(f"[{league_code}] {len(processed_fixtures)} matchs ont déjà des cotes.")

            fixtures_to_process = fixtures_to_check[~fixtures_to_check['fixture_id'].isin(processed_fixtures)]
            logger.info(f"[{league_code}] {len(fixtures_to_process)} nouveaux matchs à traiter.")

            for _, fixture in fixtures_to_process.iterrows():
                fixture_id = fixture['fixture_id']
                self.stats['fixtures_processed'] += 1

                logger.info(f"[{league_code}] Traitement du match {fixture_id}")
                odds_data = self.get_fixture_odds(fixture_id)
                if odds_data:
                    processed_odds = self.process_odds_data(fixture_id, odds_data)
                    new_odds_data.extend(processed_odds)

                time.sleep(1.5)

        if not new_odds_data:
            logger.info(f"[{league_code}] Aucune nouvelle cote à ajouter.")

        new_odds_df = pd.DataFrame(new_odds_data)
        combined_df = pd.concat([existing_odds_df, new_odds_df]).reset_index(drop=True)

        if not combined_df.empty:
            combined_df = combined_df.sort_values('collected_at', ascending=False)
            key_cols = ['fixture_id', 'bookmaker_id', 'bet_type_id', 'bet_value']
            combined_df.drop_duplicates(subset=key_cols, keep='first', inplace=True)

        combined_df.to_csv(odds_file_path, index=False, encoding='utf-8')

        if new_odds_data:
            logger.info(f"💾 Fichier de cotes pour {league_code} mis à jour: {len(new_odds_df)} nouvelles entrées ajoutées, {len(combined_df)} total.")
        else:
            logger.info(f"💾 Fichier de cotes pour {league_code} est à jour. {len(combined_df)} entrées au total.")

        self.stats['leagues_processed'].add(league_code)


    def run_collection(self, league_to_process: Optional[str] = None):
        """
        Lance le processus de collecte. Si une ligue est spécifiée, ne traite que celle-ci.
        Sinon, traite toutes les ligues.
        """
        logger.info("🚀 === DÉBUT DE LA COLLECTE DES COTES ===")
        logger.info(f"Fenêtre de temps: {self.start_date} à {self.end_date}")
        start_time = datetime.now()

        leagues_to_run = [league_to_process] if league_to_process else list(self.all_leagues.keys())

        if league_to_process and league_to_process not in self.all_leagues:
            logger.error(f"❌ Code de ligue inconnu: {league_to_process}")
            return

        for league_code in leagues_to_run:
            try:
                self.collect_league_odds(league_code)
                if len(leagues_to_run) > 1:
                    logger.info(f"⏱️ Pause de 5 secondes avant la prochaine ligue...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"❌ Erreur majeure lors du traitement de {league_code}: {e}", exc_info=True)

        duration = datetime.now() - start_time
        logger.info(f"\n🎉 === COLLECTE TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"📊 Ligues traitées: {len(self.stats['leagues_processed'])}/{len(leagues_to_run)}")
        logger.info(f"🏟️ Matchs traités: {self.stats['fixtures_processed']}")
        logger.info(f"📞 Appels API (cotes): {self.stats['odds_requests']}")
        logger.info(f"📈 Nouvelles collections de cotes: {self.stats['new_odds_collections']}")

def main():
    """
    Point d'entrée du script.
    """
    parser = argparse.ArgumentParser(description="Collecteur de cotes de football.")
    parser.add_argument("--league", type=str, help="Code de la ligue à traiter (ex: ENG1). Si non spécifié, toutes les ligues sont traitées.")
    args = parser.parse_args()

    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée. Assurez-vous que le secret est configuré.")
        return

    logger.info("✅ Clé API récupérée.")
    collector = FootballOddsCollector(RAPIDAPI_KEY)
    collector.run_collection(league_to_process=args.league)

if __name__ == "__main__":
    main()
