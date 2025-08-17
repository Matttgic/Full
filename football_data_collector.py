import requests
import pandas as pd
import os
import time
from datetime import datetime, date
import logging
from typing import Dict, List, Optional

# Configuration du logging pour debug
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('football_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootballDataCollector:
    """
    Collecteur de données football pour le Big 5 européen
    Récupère les statistiques des matchs et les sauvegarde en CSV
    """
    
    def __init__(self, rapidapi_key: str):
        """
        Initialise le collecteur avec la clé RapidAPI
        
        Args:
            rapidapi_key (str): Clé d'API RapidAPI
        """
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration des ligues Big 5 avec leurs IDs API-Football
        self.big5_leagues = {
            'ENG1': {'id': 39, 'name': 'Premier League', 'country': 'England'},
            'FRA1': {'id': 61, 'name': 'Ligue 1', 'country': 'France'},
            'ITA1': {'id': 135, 'name': 'Serie A', 'country': 'Italy'},
            'GER1': {'id': 78, 'name': 'Bundesliga', 'country': 'Germany'},
            'SPA1': {'id': 140, 'name': 'La Liga', 'country': 'Spain'}
        }
        
        # Saison actuelle (à ajuster selon la période)
        self.current_season = 2024
        
        # Création du dossier data s'il n'existe pas
        self.data_folder = "data"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            logger.info(f"Dossier '{self.data_folder}' créé")
    
    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Effectue une requête à l'API avec gestion d'erreurs
        
        Args:
            endpoint (str): Endpoint de l'API
            params (Dict): Paramètres de la requête
            
        Returns:
            Optional[Dict]: Réponse JSON ou None en cas d'erreur
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.info(f"Requête API: {endpoint} avec params: {params}")
            response = requests.get(url, headers=self.headers, params=params)
            
            # Vérification du statut HTTP
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Succès - {data.get('results', 0)} résultats récupérés")
                return data
            else:
                logger.error(f"Erreur HTTP {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de requête: {e}")
            return None
        except ValueError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            return None
    
    def get_league_fixtures(self, league_id: int, season: int) -> List[Dict]:
        """
        Récupère tous les matchs d'une ligue pour une saison
        
        Args:
            league_id (int): ID de la ligue
            season (int): Année de la saison
            
        Returns:
            List[Dict]: Liste des matchs
        """
        logger.info(f"Récupération des matchs pour la ligue {league_id}, saison {season}")
        
        params = {
            'league': league_id,
            'season': season
        }
        
        data = self.make_api_request('fixtures', params)
        
        if data and 'response' in data:
            fixtures = data['response']
            logger.info(f"{len(fixtures)} matchs récupérés pour la ligue {league_id}")
            return fixtures
        else:
            logger.warning(f"Aucun match récupéré pour la ligue {league_id}")
            return []
    
    def get_fixture_statistics(self, fixture_id: int) -> Optional[Dict]:
        """
        Récupère les statistiques détaillées d'un match
        
        Args:
            fixture_id (int): ID du match
            
        Returns:
            Optional[Dict]: Statistiques du match ou None
        """
        params = {'fixture': fixture_id}
        data = self.make_api_request('fixtures/statistics', params)
        
        if data and 'response' in data:
            return data['response']
        return None
    
    def process_fixture_data(self, fixture: Dict) -> Dict:
        """
        Traite et structure les données d'un match
        
        Args:
            fixture (Dict): Données brutes du match
            
        Returns:
            Dict: Données structurées du match
        """
        # Extraction des informations de base
        fixture_info = fixture.get('fixture', {})
        league_info = fixture.get('league', {})
        teams_info = fixture.get('teams', {})
        goals_info = fixture.get('goals', {})
        score_info = fixture.get('score', {})
        
        # Structure des données de base
        match_data = {
            'fixture_id': fixture_info.get('id'),
            'date': fixture_info.get('date'),
            'timestamp': fixture_info.get('timestamp'),
            'referee': fixture_info.get('referee'),
            'venue_name': fixture_info.get('venue', {}).get('name'),
            'venue_city': fixture_info.get('venue', {}).get('city'),
            'status_long': fixture_info.get('status', {}).get('long'),
            'status_short': fixture_info.get('status', {}).get('short'),
            'league_id': league_info.get('id'),
            'league_name': league_info.get('name'),
            'season': league_info.get('season'),
            'round': league_info.get('round'),
            'home_team_id': teams_info.get('home', {}).get('id'),
            'home_team_name': teams_info.get('home', {}).get('name'),
            'away_team_id': teams_info.get('away', {}).get('id'),
            'away_team_name': teams_info.get('away', {}).get('name'),
            'home_goals': goals_info.get('home'),
            'away_goals': goals_info.get('away'),
            'home_goals_halftime': score_info.get('halftime', {}).get('home'),
            'away_goals_halftime': score_info.get('halftime', {}).get('away'),
            'home_goals_fulltime': score_info.get('fulltime', {}).get('home'),
            'away_goals_fulltime': score_info.get('fulltime', {}).get('away'),
        }
        
        return match_data
    
    def collect_league_data(self, league_code: str) -> pd.DataFrame:
        """
        Collecte toutes les données d'une ligue
        
        Args:
            league_code (str): Code de la ligue (ex: 'ENG1')
            
        Returns:
            pd.DataFrame: DataFrame avec toutes les données de la ligue
        """
        league_info = self.big5_leagues[league_code]
        league_id = league_info['id']
        
        logger.info(f"Début de collecte pour {league_info['name']} ({league_code})")
        
        # Récupération des matchs
        fixtures = self.get_league_fixtures(league_id, self.current_season)
        
        if not fixtures:
            logger.warning(f"Aucun match trouvé pour {league_code}")
            return pd.DataFrame()
        
        processed_matches = []
        
        for i, fixture in enumerate(fixtures):
            logger.info(f"Traitement du match {i+1}/{len(fixtures)} - ID: {fixture.get('fixture', {}).get('id')}")
            
            # Traitement des données de base
            match_data = self.process_fixture_data(fixture)
            
            # Ajout des statistiques détaillées si le match est terminé
            if match_data['status_short'] == 'FT':  # Match terminé
                fixture_id = match_data['fixture_id']
                stats = self.get_fixture_statistics(fixture_id)
                
                if stats:
                    # Ajout des statistiques au match_data
                    match_data.update(self.process_statistics(stats))
                
                # Pause pour éviter de surcharger l'API
                time.sleep(0.5)
            
            processed_matches.append(match_data)
        
        # Création du DataFrame
        df = pd.DataFrame(processed_matches)
        logger.info(f"Collecte terminée pour {league_code}: {len(df)} matchs traités")
        
        return df
    
    def process_statistics(self, stats: List[Dict]) -> Dict:
        """
        Traite les statistiques détaillées d'un match
        
        Args:
            stats (List[Dict]): Statistiques brutes du match
            
        Returns:
            Dict: Statistiques structurées
        """
        stat_dict = {}
        
        if not stats or len(stats) != 2:
            return stat_dict
        
        home_stats = stats[0].get('statistics', [])
        away_stats = stats[1].get('statistics', [])
        
        # Mapping des statistiques importantes
        stat_mapping = {
            'Shots on Goal': 'shots_on_goal',
            'Shots off Goal': 'shots_off_goal',
            'Total Shots': 'total_shots',
            'Blocked Shots': 'blocked_shots',
            'Shots insidebox': 'shots_inside_box',
            'Shots outsidebox': 'shots_outside_box',
            'Fouls': 'fouls',
            'Corner Kicks': 'corner_kicks',
            'Offsides': 'offsides',
            'Ball Possession': 'possession',
            'Yellow Cards': 'yellow_cards',
            'Red Cards': 'red_cards',
            'Goalkeeper Saves': 'goalkeeper_saves',
            'Total passes': 'total_passes',
            'Passes accurate': 'passes_accurate',
            'Passes %': 'passes_percentage'
        }
        
        # Extraction des stats pour l'équipe domicile
        for stat in home_stats:
            stat_type = stat.get('type')
            if stat_type in stat_mapping:
                key = f"home_{stat_mapping[stat_type]}"
                value = stat.get('value')
                # Conversion en numérique si possible
                if value and value != 'null':
                    try:
                        if '%' in str(value):
                            stat_dict[key] = float(str(value).replace('%', ''))
                        else:
                            stat_dict[key] = float(value) if '.' in str(value) else int(value)
                    except (ValueError, TypeError):
                        stat_dict[key] = value
                else:
                    stat_dict[key] = None
        
        # Extraction des stats pour l'équipe extérieure
        for stat in away_stats:
            stat_type = stat.get('type')
            if stat_type in stat_mapping:
                key = f"away_{stat_mapping[stat_type]}"
                value = stat.get('value')
                # Conversion en numérique si possible
                if value and value != 'null':
                    try:
                        if '%' in str(value):
                            stat_dict[key] = float(str(value).replace('%', ''))
                        else:
                            stat_dict[key] = float(value) if '.' in str(value) else int(value)
                    except (ValueError, TypeError):
                        stat_dict[key] = value
                else:
                    stat_dict[key] = None
        
        return stat_dict
    
    def save_to_csv(self, df: pd.DataFrame, league_code: str) -> None:
        """
        Sauvegarde le DataFrame en CSV
        
        Args:
            df (pd.DataFrame): DataFrame à sauvegarder
            league_code (str): Code de la ligue
        """
        if df.empty:
            logger.warning(f"DataFrame vide pour {league_code}, pas de sauvegarde")
            return
        
        filename = f"{league_code}.csv"
        filepath = os.path.join(self.data_folder, filename)
        
        try:
            # Tri par date
            if 'date' in df.columns:
                df = df.sort_values('date')
            
            # Sauvegarde
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"Données sauvegardées: {filepath} ({len(df)} lignes)")
            
            # Affichage d'un aperçu
            logger.info(f"Aperçu des colonnes: {list(df.columns)}")
            logger.info(f"Période des données: {df['date'].min()} à {df['date'].max()}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de {filepath}: {e}")
    
    def run_full_collection(self) -> None:
        """
        Lance la collecte complète pour toutes les ligues du Big 5
        """
        logger.info("=== DÉBUT DE LA COLLECTE BIG 5 ===")
        start_time = datetime.now()
        
        for league_code in self.big5_leagues.keys():
            try:
                logger.info(f"\n--- Collecte de {league_code} ---")
                
                # Collecte des données
                df = self.collect_league_data(league_code)
                
                # Sauvegarde
                self.save_to_csv(df, league_code)
                
                # Pause entre les ligues pour respecter les limites d'API
                logger.info("Pause de 5 secondes avant la prochaine ligue...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur lors de la collecte de {league_code}: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"\n=== COLLECTE TERMINÉE ===")
        logger.info(f"Durée totale: {duration}")
        logger.info(f"Fichiers générés dans le dossier '{self.data_folder}'")

def main():
    """
    Fonction principale - Point d'entrée du script
    """
    # ⚠️ REMPLACE 'YOUR_RAPIDAPI_KEY' par ta vraie clé RapidAPI
    RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY"
    
    if RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY":
        logger.error("⚠️ Veuillez configurer votre clé RapidAPI dans la variable RAPIDAPI_KEY")
        return
    
    # Création du collecteur
    collector = FootballDataCollector(RAPIDAPI_KEY)
    
    # Lancement de la collecte
    collector.run_full_collection()

if __name__ == "__main__":
    main()
