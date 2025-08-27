"""
Ce script est le collecteur principal de données de matchs de football.

Rôle :
- Se connecte à l'API de football pour récupérer les données des matchs.
- Itère sur une liste prédéfinie de 15 ligues majeures.
- Pour chaque ligue, collecte les données de tous les matchs pour les saisons spécifiées
  (par exemple, 2024 et 2025).
- Pour les matchs terminés, récupère également les statistiques détaillées
  (tirs, possession, etc.).
- Sauvegarde les données de chaque ligue dans un fichier CSV séparé dans `data/matches/`.

Note importante : La limite de collecte aux 365 derniers jours a été retirée
pour permettre une analyse historique complète.
"""
import requests
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional
from src.config import ALL_LEAGUES, SEASONS_TO_COLLECT

# Configuration du logging pour debug
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/football_data_extended.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootballDataCollectorExtended:
    """
    Collecteur de données football pour TOUTES les ligues (15 au total).
    Récupère les statistiques des matchs et les sauvegarde dans data/matches/
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
        
        # Utilisation de la configuration centralisée
        self.all_leagues = ALL_LEAGUES
        self.seasons_to_collect = SEASONS_TO_COLLECT

        # Période de collecte (365 derniers jours)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=365)
        
        # Création de la structure de dossiers
        self.matches_folder = os.path.join("data", "matches")
        os.makedirs(self.matches_folder, exist_ok=True)
        logger.info(f"Dossier pour les matchs assuré d'exister: '{self.matches_folder}'")
    
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
                results_count = data.get('results', 0)
                logger.info(f"Succès - {results_count} résultats récupérés")
                
                # Debug de la réponse si erreurs
                if 'errors' in data and data['errors']:
                    logger.warning(f"Erreurs API: {data['errors']}")
                
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
    
    def get_league_fixtures_multiple_seasons(self, league_id: int) -> List[Dict]:
        """
        Récupère tous les matchs d'une ligue pour les saisons 2024 et 2025
        Puis filtre pour garder seulement les 365 derniers jours
        
        Args:
            league_id (int): ID de la ligue
            
        Returns:
            List[Dict]: Liste des matchs filtrés
        """
        logger.info(f"Récupération des matchs pour la ligue {league_id} pour les saisons: {self.seasons_to_collect}")
        
        all_fixtures = []
        
        # Récupération pour chaque saison
        for season in self.seasons_to_collect:
            logger.info(f"📅 Récupération saison {season} pour la ligue {league_id}")
            
            params = {
                'league': league_id,
                'season': season
            }
            
            data = self.make_api_request('fixtures', params)
            
            if data and 'response' in data:
                season_fixtures = data['response']
                logger.info(f"✅ Saison {season}: {len(season_fixtures)} matchs récupérés")
                all_fixtures.extend(season_fixtures)
            else:
                logger.warning(f"❌ Saison {season}: Aucun match récupéré")
            
            # Pause entre les saisons pour respecter les limites d'API
            time.sleep(1)
        
        logger.info(f"📊 Total des matchs collectés pour la ligue {league_id}: {len(all_fixtures)} matchs")
        
        return all_fixtures
    
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
    
    def collect_league_data(self, league_code: str) -> pd.DataFrame:
        """
        Collecte toutes les données d'une ligue pour les 365 derniers jours.
        """
        league_info = self.all_leagues[league_code]
        league_id = league_info['id']
        
        logger.info(f"🏆 Début de collecte pour {league_info['name']} ({league_code})")
        
        # Récupération des matchs des 365 derniers jours
        fixtures = self.get_league_fixtures_multiple_seasons(league_id)
        
        if not fixtures:
            logger.warning(f"❌ Aucun match trouvé pour {league_code}")
            return pd.DataFrame()
        
        processed_matches = []
        finished_matches = 0
        
        for i, fixture in enumerate(fixtures):
            fixture_id = fixture.get('fixture', {}).get('id')
            status = fixture.get('fixture', {}).get('status', {}).get('short', '')
            
            logger.info(f"⚽ Traitement match {i+1}/{len(fixtures)} - ID: {fixture_id} - Status: {status}")
            
            # Traitement des données de base
            match_data = self.process_fixture_data(fixture)
            
            # Ajout des statistiques détaillées si le match est terminé
            if status == 'FT':  # Match terminé
                finished_matches += 1
                logger.info(f"📊 Récupération des stats pour le match terminé {fixture_id}")
                
                stats = self.get_fixture_statistics(fixture_id)
                
                if stats:
                    # Ajout des statistiques au match_data
                    match_data.update(self.process_statistics(stats))
                    logger.debug(f"✅ Stats ajoutées pour le match {fixture_id}")
                else:
                    logger.warning(f"⚠️ Pas de stats disponibles pour le match {fixture_id}")
                
                # Pause pour éviter de surcharger l'API
                time.sleep(0.5)
            else:
                logger.debug(f"⏳ Match {fixture_id} non terminé (status: {status})")
            
            processed_matches.append(match_data)
        
        # Création du DataFrame
        df = pd.DataFrame(processed_matches)
        
        logger.info(f"✅ Collecte terminée pour {league_code}:")
        logger.info(f"   📊 Total matchs: {len(df)}")
        logger.info(f"   🏁 Matchs terminés: {finished_matches}")
        logger.info(f"   ⏳ Matchs en cours/programmés: {len(df) - finished_matches}")
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, league_code: str) -> None:
        """
        Sauvegarde le DataFrame en CSV
        
        Args:
            df (pd.DataFrame): DataFrame à sauvegarder
            league_code (str): Code de la ligue
        """
        if df.empty:
            logger.warning(f"❌ DataFrame vide pour {league_code}, pas de sauvegarde")
            return
        
        filename = f"{league_code}.csv"
        filepath = os.path.join(self.matches_folder, filename)
        
        try:
            # Tri par date
            if 'date' in df.columns:
                df = df.sort_values('date')
            
            # Sauvegarde
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Données sauvegardées: {filepath} ({len(df)} lignes)")
            
            # Affichage d'un aperçu
            logger.info(f"📋 Aperçu des colonnes: {len(df.columns)} colonnes")
            if 'date' in df.columns and len(df) > 0:
                logger.info(f"📅 Période des données: {df['date'].min()} à {df['date'].max()}")
                logger.info(f"🔢 Nombre de matchs: {len(df)}")
            else:
                logger.info("ℹ️ Aucune donnée de date disponible")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de {filepath}: {e}")
    
    def run_full_collection(self) -> None:
        """
        Lance la collecte complète pour TOUTES les ligues.
        """
        logger.info("🚀 === DÉBUT DE LA COLLECTE ÉTENDUE (365 DERNIERS JOURS) ===")
        logger.info(f"📅 Période de collecte des matchs: du {self.start_date} au {self.end_date}")
        logger.info(f"🏆 Saisons analysées: {self.seasons_to_collect}")
        start_time = datetime.now()
        
        successful_collections = 0
        
        for league_code in self.all_leagues.keys():
            try:
                logger.info(f"\n🏟️ --- Collecte de {league_code} ---")
                
                # Collecte des données
                df = self.collect_league_data(league_code)
                
                # Sauvegarde
                if not df.empty:
                    self.save_to_csv(df, league_code)
                    successful_collections += 1
                
                # Pause entre les ligues pour respecter les limites d'API
                logger.info("⏱️ Pause de 5 secondes avant la prochaine ligue...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de la collecte de {league_code}: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\n🎉 === COLLECTE TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"✅ Ligues traitées avec succès: {successful_collections}/{len(self.all_leagues)}")
        logger.info(f"📁 Fichiers générés dans le dossier '{self.matches_folder}'")
        
        # Résumé des fichiers créés
        if os.path.exists(self.matches_folder):
            csv_files = [f for f in os.listdir(self.matches_folder) if f.endswith('.csv')]
            logger.info(f"📊 Fichiers CSV créés: {csv_files}")

def main():
    """
    Fonction principale - Point d'entrée du script
    """
    # Récupération de la clé API depuis les variables d'environnement (GitHub Secrets)
    import os
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        logger.error("💡 Assurez-vous que le secret RAPIDAPI_KEY est configuré dans GitHub")
        return
    
    logger.info("✅ Clé API récupérée depuis les variables d'environnement")
    
    # Création du collecteur
    collector = FootballDataCollectorExtended(RAPIDAPI_KEY)
    
    # Lancement de la collecte
    collector.run_full_collection()

if __name__ == "__main__":
    main() 
