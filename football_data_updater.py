import requests
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional

# Configuration du logging pour la mise à jour
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('football_data_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootballDataUpdater:
    """
    Mise à jour incrémentale des données football
    Maintient une fenêtre glissante de 365 jours en ajoutant les nouveaux matchs
    et supprimant les anciens
    """
    
    def __init__(self, rapidapi_key: str):
        """
        Initialise le updater avec la clé RapidAPI
        """
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration de toutes les ligues (Big 5 + nouvelles ligues)
        self.all_leagues = {
            # Big 5
            'ENG1': {'id': 39, 'name': 'Premier League', 'country': 'England'},
            'FRA1': {'id': 61, 'name': 'Ligue 1', 'country': 'France'},
            'ITA1': {'id': 135, 'name': 'Serie A', 'country': 'Italy'},
            'GER1': {'id': 78, 'name': 'Bundesliga', 'country': 'Germany'},
            'SPA1': {'id': 140, 'name': 'La Liga', 'country': 'Spain'},
            # Nouvelles ligues
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
        
        # Configuration des dates
        self.today = datetime.now().date()
        self.cutoff_date = self.today - timedelta(days=365)  # Date limite (365 jours)
        self.update_start_date = self.today - timedelta(days=14)  # Derniers 14 jours pour les mises à jour
        
        # Dossier de données
        self.data_folder = "data"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            logger.info(f"Dossier '{self.data_folder}' créé")
    
    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API avec gestion d'erreurs"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f"Requête API: {endpoint} avec params: {params}")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results_count = data.get('results', 0)
                logger.debug(f"Succès - {results_count} résultats récupérés")
                
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
    
    def load_existing_data(self, league_code: str) -> pd.DataFrame:
        """
        Charge les données existantes d'une ligue depuis le fichier CSV
        """
        filepath = os.path.join(self.data_folder, f"{league_code}.csv")
        
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                logger.info(f"📂 Données existantes chargées pour {league_code}: {len(df)} matchs")
                
                # Conversion de la colonne date si elle existe
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date']).dt.date
                
                return df
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement de {filepath}: {e}")
                return pd.DataFrame()
        else:
            logger.info(f"📂 Aucun fichier existant pour {league_code}")
            return pd.DataFrame()
    
    def filter_by_date_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre le DataFrame pour garder seulement les matchs des 365 derniers jours
        """
        if df.empty or 'date' not in df.columns:
            return df
        
        # Conversion des dates si nécessaire
        if df['date'].dtype == 'object':
            df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Filtrage
        before_count = len(df)
        df_filtered = df[df['date'] >= self.cutoff_date].copy()
        after_count = len(df_filtered)
        
        removed_count = before_count - after_count
        if removed_count > 0:
            logger.info(f"🗑️ Suppression de {removed_count} matchs trop anciens (> 365 jours)")
        
        return df_filtered
    
    def get_recent_fixtures(self, league_id: int, league_code: str) -> List[Dict]:
        """
        Récupère les matchs récents d'une ligue (14 derniers jours + 7 prochains jours)
        """
        logger.info(f"🔄 Récupération des matchs récents pour {league_code}")
        
        # Date de fin : dans 7 jours (pour capturer les matchs programmés)
        end_date = self.today + timedelta(days=7)
        
        logger.info(f"📅 Période de mise à jour: {self.update_start_date} à {end_date}")
        
        all_fixtures = []
        
        # Récupération pour les saisons 2024 et 2025
        for season in [2024, 2025]:
            params = {
                'league': league_id,
                'season': season,
                'from': self.update_start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            }
            
            data = self.make_api_request('fixtures', params)
            
            if data and 'response' in data:
                season_fixtures = data['response']
                logger.info(f"✅ Saison {season}: {len(season_fixtures)} matchs récents récupérés")
                all_fixtures.extend(season_fixtures)
            
            time.sleep(0.5)  # Pause pour respecter les limites d'API
        
        logger.info(f"📊 Total matchs récents récupérés: {len(all_fixtures)}")
        return all_fixtures
    
    def get_fixture_statistics(self, fixture_id: int) -> Optional[Dict]:
        """Récupère les statistiques détaillées d'un match"""
        params = {'fixture': fixture_id}
        data = self.make_api_request('fixtures/statistics', params)
        
        if data and 'response' in data:
            return data['response']
        return None
    
    def process_fixture_data(self, fixture: Dict) -> Dict:
        """Traite et structure les données d'un match"""
        fixture_info = fixture.get('fixture', {})
        league_info = fixture.get('league', {})
        teams_info = fixture.get('teams', {})
        goals_info = fixture.get('goals', {})
        score_info = fixture.get('score', {})
        
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
        """Traite les statistiques détaillées d'un match"""
        stat_dict = {}
        
        if not stats or len(stats) != 2:
            return stat_dict
        
        home_stats = stats[0].get('statistics', [])
        away_stats = stats[1].get('statistics', [])
        
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
    
    def update_league_data(self, league_code: str) -> bool:
        """
        Met à jour les données d'une ligue de manière incrémentale
        """
        league_info = self.all_leagues[league_code]
        league_id = league_info['id']
        
        logger.info(f"🏆 Mise à jour incrémentale pour {league_info['name']} ({league_code})")
        
        # 1. Charger les données existantes
        existing_df = self.load_existing_data(league_code)
        
        # 2. Supprimer les matchs trop anciens (> 365 jours)
        if not existing_df.empty:
            existing_df = self.filter_by_date_range(existing_df)
        
        # 3. Récupérer les matchs récents
        recent_fixtures = self.get_recent_fixtures(league_id, league_code)
        
        if not recent_fixtures:
            logger.warning(f"❌ Aucun match récent trouvé pour {league_code}")
            # Sauvegarder quand même les données filtrées
            if not existing_df.empty:
                self.save_to_csv(existing_df, league_code)
            return False
        
        # 4. Traiter les nouveaux matchs
        new_matches = []
        stats_added = 0
        
        for i, fixture in enumerate(recent_fixtures):
            fixture_id = fixture.get('fixture', {}).get('id')
            status = fixture.get('fixture', {}).get('status', {}).get('short', '')
            
            logger.debug(f"⚽ Traitement match récent {i+1}/{len(recent_fixtures)} - ID: {fixture_id}")
            
            # Vérifier si le match existe déjà
            if not existing_df.empty and 'fixture_id' in existing_df.columns:
                if fixture_id in existing_df['fixture_id'].values:
                    # Match existant - mettre à jour si terminé et pas encore de stats
                    existing_match = existing_df[existing_df['fixture_id'] == fixture_id].iloc[0]
                    if status == 'FT' and pd.isna(existing_match.get('home_shots_on_goal')):
                        logger.info(f"📊 Mise à jour des stats pour le match existant {fixture_id}")
                        
                        # Supprimer l'ancienne version
                        existing_df = existing_df[existing_df['fixture_id'] != fixture_id]
                        
                        # Ajouter la nouvelle version avec stats
                        match_data = self.process_fixture_data(fixture)
                        stats = self.get_fixture_statistics(fixture_id)
                        if stats:
                            match_data.update(self.process_statistics(stats))
                            stats_added += 1
                        
                        new_matches.append(match_data)
                        time.sleep(0.5)
                    continue
            
            # Nouveau match
            match_data = self.process_fixture_data(fixture)
            
            # Ajouter les statistiques si le match est terminé
            if status == 'FT':
                logger.debug(f"📊 Récupération des stats pour le nouveau match terminé {fixture_id}")
                stats = self.get_fixture_statistics(fixture_id)
                if stats:
                    match_data.update(self.process_statistics(stats))
                    stats_added += 1
                time.sleep(0.5)
            
            new_matches.append(match_data)
        
        # 5. Combiner les données existantes et nouvelles
        if new_matches:
            new_df = pd.DataFrame(new_matches)
            
            if not existing_df.empty:
                # Combiner et supprimer les doublons
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['fixture_id'], keep='last')
            else:
                combined_df = new_df
        else:
            combined_df = existing_df
        
        # 6. Filtrage final par date et tri
        combined_df = self.filter_by_date_range(combined_df)
        
        if 'date' in combined_df.columns:
            combined_df = combined_df.sort_values('date')
        
        # 7. Sauvegarde
        self.save_to_csv(combined_df, league_code)
        
        logger.info(f"✅ Mise à jour terminée pour {league_code}:")
        logger.info(f"   📊 Total final: {len(combined_df)} matchs")
        logger.info(f"   🆕 Nouveaux matchs traités: {len(new_matches)}")
        logger.info(f"   📈 Stats ajoutées: {stats_added}")
        
        return True
    
    def save_to_csv(self, df: pd.DataFrame, league_code: str) -> None:
        """Sauvegarde le DataFrame en CSV"""
        if df.empty:
            logger.warning(f"❌ DataFrame vide pour {league_code}, pas de sauvegarde")
            return
        
        filename = f"{league_code}.csv"
        filepath = os.path.join(self.data_folder, filename)
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Données sauvegardées: {filepath} ({len(df)} lignes)")
            
            if 'date' in df.columns and len(df) > 0:
                logger.info(f"📅 Période: {df['date'].min()} à {df['date'].max()}")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de {filepath}: {e}")
    
    def run_incremental_update(self) -> None:
        """
        Lance la mise à jour incrémentale pour toutes les ligues
        """
        logger.info("🚀 === DÉBUT DE LA MISE À JOUR INCRÉMENTALE ===")
        logger.info(f"📅 Date limite (365 jours): {self.cutoff_date}")
        logger.info(f"🔄 Période de mise à jour: {self.update_start_date} à {self.today}")
        
        start_time = datetime.now()
        successful_updates = 0
        
        for league_code in self.all_leagues.keys():
            try:
                logger.info(f"\n🏟️ --- Mise à jour de {league_code} ---")
                
                success = self.update_league_data(league_code)
                if success:
                    successful_updates += 1
                
                # Pause entre les ligues
                logger.info("⏱️ Pause de 3 secondes...")
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de la mise à jour de {league_code}: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"\n🎉 === MISE À JOUR TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"✅ Ligues mises à jour avec succès: {successful_updates}/{len(self.all_leagues)}")
        logger.info(f"📁 Fenêtre de données maintenue: 365 derniers jours")

def main():
    """Fonction principale"""
    import os
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        return
    
    logger.info("✅ Clé API récupérée depuis les variables d'environnement")
    
    # Création du updater et lancement
    updater = FootballDataUpdater(RAPIDAPI_KEY)
    updater.run_incremental_update()

if __name__ == "__main__":
    main()
