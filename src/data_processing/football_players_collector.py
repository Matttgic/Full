import requests
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('football_players.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootballPlayersCollector:
    """
    Collecteur de statistiques individuelles des joueurs
    Récupère les stats détaillées pour tous les matchs des 365 derniers jours
    """
    
    def __init__(self, rapidapi_key: str):
        """Initialise le collecteur avec la clé RapidAPI"""
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration des ligues (toutes celles que vous avez)
        self.leagues = {
            'ENG1': 'Premier League',
            'FRA1': 'Ligue 1', 
            'ITA1': 'Serie A',
            'GER1': 'Bundesliga',
            'SPA1': 'La Liga',
            'NED1': 'Eredivisie',
            'POR1': 'Primeira Liga',
            'BEL1': 'Jupiler Pro League',
            'ENG2': 'Championship',
            'FRA2': 'Ligue 2',
            'ITA2': 'Serie B',
            'GER2': '2. Bundesliga',
            'SPA2': 'Segunda División',
            'TUR1': 'Süper Lig',
            'SAU1': 'Saudi Pro League'
        }
        
        # Structure des dossiers
        self.data_folder = "data"
        self.matches_folder = os.path.join(self.data_folder, "matches")
        self.players_folder = os.path.join(self.data_folder, "players")
        self.player_stats_folder = os.path.join(self.players_folder, "player_stats")
        self.match_lineups_folder = os.path.join(self.players_folder, "match_lineups")
        self.team_rosters_folder = os.path.join(self.players_folder, "team_rosters")
        
        # Création des dossiers
        for folder in [self.matches_folder, self.player_stats_folder, 
                      self.match_lineups_folder, self.team_rosters_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
                logger.info(f"Dossier créé: {folder}")
        
        # Statistiques de collecte
        self.stats = {
            'total_matches_processed': 0,
            'total_players_found': 0,
            'total_api_calls': 0,
            'failed_requests': 0,
            'leagues_processed': 0
        }
    
    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API avec gestion d'erreurs et statistiques"""
        url = f"{self.base_url}/{endpoint}"
        self.stats['total_api_calls'] += 1
        
        try:
            logger.debug(f"API Request #{self.stats['total_api_calls']}: {endpoint}")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results_count = data.get('results', 0)
                logger.debug(f"✅ {results_count} résultats récupérés")
                
                if 'errors' in data and data['errors']:
                    logger.warning(f"⚠️ Erreurs API: {data['errors']}")
                
                return data
            else:
                logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                self.stats['failed_requests'] += 1
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur de requête: {e}")
            self.stats['failed_requests'] += 1
            return None
        except ValueError as e:
            logger.error(f"❌ Erreur de parsing JSON: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    def load_match_data(self, league_code: str) -> pd.DataFrame:
        """Charge les données de matchs existantes pour une ligue"""
        filepath = os.path.join(self.matches_folder, f"{league_code}.csv")
        
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                logger.info(f"📂 Matchs chargés pour {league_code}: {len(df)} matchs")
                return df
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement de {filepath}: {e}")
                return pd.DataFrame()
        else:
            logger.warning(f"📂 Aucun fichier de matchs trouvé pour {league_code}")
            return pd.DataFrame()
    
    def get_fixture_players(self, fixture_id: int) -> Optional[Dict]:
        """Récupère les stats des joueurs pour un match donné"""
        params = {'fixture': fixture_id}
        data = self.make_api_request('fixtures/players', params)
        
        if data and 'response' in data:
            return data['response']
        return None
    
    def process_player_stats(self, player_data: Dict, fixture_id: int, 
                           league_code: str, match_date: str) -> List[Dict]:
        """Traite les données d'un joueur pour un match"""
        processed_stats = []
        
        team_info = player_data.get('team', {})
        players = player_data.get('players', [])
        
        for player_info in players:
            player = player_info.get('player', {})
            stats_list = player_info.get('statistics', [])
            
            if not stats_list:
                continue
                
            # Un joueur peut avoir plusieurs entrées de stats (ex: changement de poste)
            for stats in stats_list:
                games = stats.get('games', {})
                
                processed_stat = {
                    # Identifiants
                    'fixture_id': fixture_id,
                    'league_code': league_code,
                    'match_date': match_date,
                    'player_id': player.get('id'),
                    'player_name': player.get('name'),
                    'team_id': team_info.get('id'),
                    'team_name': team_info.get('name'),
                    
                    # Infos du match
                    'minutes': games.get('minutes'),
                    'position': games.get('position'),
                    'shirt_number': games.get('number'),
                    'rating': games.get('rating'),
                    'captain': games.get('captain', False),
                    'substitute': games.get('substitute', False),
                    
                    # Statistiques offensives
                    'goals_scored': stats.get('goals', {}).get('total'),
                    'goals_conceded': stats.get('goals', {}).get('conceded'),
                    'assists': stats.get('goals', {}).get('assists'),
                    'saves': stats.get('goals', {}).get('saves'),
                    
                    # Tirs
                    'shots_total': stats.get('shots', {}).get('total'),
                    'shots_on_target': stats.get('shots', {}).get('on'),
                    
                    # Passes
                    'passes_total': stats.get('passes', {}).get('total'),
                    'passes_key': stats.get('passes', {}).get('key'),
                    'passes_accuracy': stats.get('passes', {}).get('accuracy'),
                    
                    # Défense
                    'tackles_total': stats.get('tackles', {}).get('total'),
                    'blocks': stats.get('tackles', {}).get('blocks'),
                    'interceptions': stats.get('tackles', {}).get('interceptions'),
                    
                    # Duels
                    'duels_total': stats.get('duels', {}).get('total'),
                    'duels_won': stats.get('duels', {}).get('won'),
                    
                    # Dribbles
                    'dribbles_attempts': stats.get('dribbles', {}).get('attempts'),
                    'dribbles_success': stats.get('dribbles', {}).get('success'),
                    'dribbles_past': stats.get('dribbles', {}).get('past'),
                    
                    # Fautes et cartons
                    'fouls_drawn': stats.get('fouls', {}).get('drawn'),
                    'fouls_committed': stats.get('fouls', {}).get('committed'),
                    'yellow_cards': stats.get('cards', {}).get('yellow'),
                    'red_cards': stats.get('cards', {}).get('red'),
                    
                    # Penalties
                    'penalty_won': stats.get('penalty', {}).get('won'),
                    'penalty_committed': stats.get('penalty', {}).get('commited'),
                    'penalty_scored': stats.get('penalty', {}).get('scored'),
                    'penalty_missed': stats.get('penalty', {}).get('missed'),
                    'penalty_saved': stats.get('penalty', {}).get('saved'),
                    
                    # Hors-jeu
                    'offsides': stats.get('offsides')
                }
                
                processed_stats.append(processed_stat)
        
        return processed_stats
    
    def collect_league_players(self, league_code: str) -> None:
        """Collecte les stats des joueurs pour tous les matchs d'une ligue"""
        logger.info(f"🏆 Début de collecte joueurs pour {league_code} ({self.leagues[league_code]})")
        
        # Charger les données de matchs
        matches_df = self.load_match_data(league_code)
        
        if matches_df.empty:
            logger.warning(f"❌ Aucun match trouvé pour {league_code}")
            return
        
        # Filtrer les matchs terminés seulement
        finished_matches = matches_df[matches_df['status_short'] == 'FT'].copy()
        logger.info(f"📊 {len(finished_matches)} matchs terminés à traiter pour {league_code}")
        
        if finished_matches.empty:
            logger.warning(f"❌ Aucun match terminé pour {league_code}")
            return
        
        # Listes pour stocker toutes les données
        all_player_stats = []
        all_lineups = []
        all_teams = {}
        
        # Traitement de chaque match
        for index, match in finished_matches.iterrows():
            fixture_id = match['fixture_id']
            match_date = match['date']
            
            logger.info(f"⚽ Traitement match {index+1}/{len(finished_matches)} - ID: {fixture_id}")
            
            # Récupération des stats joueurs
            players_data = self.get_fixture_players(fixture_id)
            
            if not players_data:
                logger.warning(f"⚠️ Pas de données joueurs pour le match {fixture_id}")
                continue
            
            # Traitement des données de chaque équipe
            match_lineup = {
                'fixture_id': fixture_id,
                'league_code': league_code,
                'match_date': match_date,
                'home_team': match.get('home_team_name'),
                'away_team': match.get('away_team_name'),
                'teams': []
            }
            
            for team_data in players_data:
                team_info = team_data.get('team', {})
                team_id = team_info.get('id')
                team_name = team_info.get('name')
                
                # Stats individuelles des joueurs
                player_stats = self.process_player_stats(
                    team_data, fixture_id, league_code, match_date
                )
                all_player_stats.extend(player_stats)
                
                # Composition d'équipe
                team_composition = {
                    'team_id': team_id,
                    'team_name': team_name,
                    'players_count': len(team_data.get('players', []))
                }
                match_lineup['teams'].append(team_composition)
                
                # Effectif d'équipe (pour later)
                if team_id not in all_teams:
                    all_teams[team_id] = {
                        'team_id': team_id,
                        'team_name': team_name,
                        'league_code': league_code,
                        'players': set()
                    }
                
                # Ajouter les joueurs à l'effectif
                for player_info in team_data.get('players', []):
                    player = player_info.get('player', {})
                    all_teams[team_id]['players'].add((
                        player.get('id'),
                        player.get('name')
                    ))
            
            all_lineups.append(match_lineup)
            self.stats['total_matches_processed'] += 1
            
            # Pause pour respecter les limites d'API
            time.sleep(0.5)
        
        # Sauvegarde des données
        self.save_player_stats(all_player_stats, league_code)
        self.save_match_lineups(all_lineups, league_code)
        self.save_team_rosters(all_teams, league_code)
        
        self.stats['leagues_processed'] += 1
        self.stats['total_players_found'] += len(all_player_stats)
        
        logger.info(f"✅ {league_code} terminé - {len(all_player_stats)} stats joueurs collectées")
    
    def save_player_stats(self, player_stats: List[Dict], league_code: str) -> None:
        """Sauvegarde les stats individuelles des joueurs"""
        if not player_stats:
            logger.warning(f"❌ Aucune stat joueur à sauvegarder pour {league_code}")
            return
        
        df = pd.DataFrame(player_stats)
        filepath = os.path.join(self.player_stats_folder, f"{league_code}_players.csv")
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Stats joueurs sauvegardées: {filepath} ({len(df)} lignes)")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde stats joueurs {league_code}: {e}")
    
    def save_match_lineups(self, lineups: List[Dict], league_code: str) -> None:
        """Sauvegarde les compositions par match"""
        if not lineups:
            logger.warning(f"❌ Aucune composition à sauvegarder pour {league_code}")
            return
        
        # Aplatir les données pour CSV
        flattened_lineups = []
        for lineup in lineups:
            base_info = {
                'fixture_id': lineup['fixture_id'],
                'league_code': lineup['league_code'],
                'match_date': lineup['match_date'],
                'home_team': lineup['home_team'],
                'away_team': lineup['away_team']
            }
            
            for i, team in enumerate(lineup['teams']):
                team_info = base_info.copy()
                team_info.update({
                    f'team_{i+1}_id': team['team_id'],
                    f'team_{i+1}_name': team['team_name'],
                    f'team_{i+1}_players_count': team['players_count']
                })
                if i == 0:  # Premier équipe seulement
                    flattened_lineups.append(team_info)
                else:  # Mise à jour avec info deuxième équipe
                    if flattened_lineups:
                        flattened_lineups[-1].update({
                            f'team_{i+1}_id': team['team_id'],
                            f'team_{i+1}_name': team['team_name'],
                            f'team_{i+1}_players_count': team['players_count']
                        })
        
        df = pd.DataFrame(flattened_lineups)
        filepath = os.path.join(self.match_lineups_folder, f"{league_code}_lineups.csv")
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Compositions sauvegardées: {filepath} ({len(df)} matchs)")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde compositions {league_code}: {e}")
    
    def save_team_rosters(self, teams: Dict, league_code: str) -> None:
        """Sauvegarde les effectifs par équipe"""
        if not teams:
            logger.warning(f"❌ Aucun effectif à sauvegarder pour {league_code}")
            return
        
        rosters = []
        for team_id, team_info in teams.items():
            for player_id, player_name in team_info['players']:
                rosters.append({
                    'league_code': league_code,
                    'team_id': team_id,
                    'team_name': team_info['team_name'],
                    'player_id': player_id,
                    'player_name': player_name
                })
        
        df = pd.DataFrame(rosters)
        filepath = os.path.join(self.team_rosters_folder, f"{league_code}_rosters.csv")
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Effectifs sauvegardés: {filepath} ({len(df)} joueurs)")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde effectifs {league_code}: {e}")
    
    def run_full_collection(self) -> None:
        """Lance la collecte complète pour toutes les ligues"""
        logger.info("🚀 === DÉBUT DE LA COLLECTE DES STATS JOUEURS ===")
        logger.info(f"🏆 Ligues à traiter: {list(self.leagues.keys())}")
        
        start_time = datetime.now()
        
        for league_code in self.leagues.keys():
            try:
                logger.info(f"\n🏟️ --- Collecte joueurs {league_code} ---")
                self.collect_league_players(league_code)
                
                # Pause entre les ligues
                logger.info("⏱️ Pause de 10 secondes avant la prochaine ligue...")
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de la collecte joueurs {league_code}: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Résumé final
        logger.info(f"\n🎉 === COLLECTE JOUEURS TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"✅ Ligues traitées: {self.stats['leagues_processed']}/{len(self.leagues)}")
        logger.info(f"📊 Matchs traités: {self.stats['total_matches_processed']}")
        logger.info(f"🏃 Stats joueurs collectées: {self.stats['total_players_found']}")
        logger.info(f"🌐 Requêtes API: {self.stats['total_api_calls']}")
        logger.info(f"❌ Requêtes échouées: {self.stats['failed_requests']}")
        
        # Résumé des fichiers créés
        logger.info(f"\n📁 === FICHIERS CRÉÉS ===")
        for folder_name, folder_path in [
            ("Stats joueurs", self.player_stats_folder),
            ("Compositions", self.match_lineups_folder), 
            ("Effectifs", self.team_rosters_folder)
        ]:
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
            logger.info(f"📊 {folder_name}: {len(csv_files)} fichiers")

def main():
    """Fonction principale"""
    import os
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        return
    
    logger.info("✅ Clé API récupérée depuis les variables d'environnement")
    
    # Création du collecteur et lancement
    collector = FootballPlayersCollector(RAPIDAPI_KEY)
    collector.run_full_collection()

if __name__ == "__main__":
    main()
