import requests
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional, Set, Tuple
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('football_players_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootballPlayersUpdater:
    """
    Mise à jour incrémentale des statistiques des joueurs
    - Met à jour uniquement les nouveaux matchs de la dernière semaine
    - Maintient une fenêtre glissante de 365 jours
    - Optimise les appels API
    """
    
    def __init__(self, rapidapi_key: str):
        """Initialise l'updater avec la clé RapidAPI"""
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration des ligues
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
        
        # Dates pour la mise à jour
        self.today = date.today()
        self.cutoff_date = self.today - timedelta(days=365)  # Fenêtre 365 jours
        self.update_from = self.today - timedelta(days=7)   # Dernière semaine
        
        logger.info(f"📅 Date limite (365 jours): {self.cutoff_date}")
        logger.info(f"🔄 Mise à jour depuis: {self.update_from}")
        
        # Statistiques
        self.stats = {
            'leagues_processed': 0,
            'new_matches_found': 0,
            'new_player_stats': 0,
            'api_calls': 0,
            'failed_requests': 0,
            'files_updated': 0
        }
    
    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API avec gestion d'erreurs"""
        url = f"{self.base_url}/{endpoint}"
        self.stats['api_calls'] += 1
        
        try:
            logger.debug(f"API Request #{self.stats['api_calls']}: {endpoint}")
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                self.stats['failed_requests'] += 1
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erreur de requête: {e}")
            self.stats['failed_requests'] += 1
            return None
    
    def load_existing_data(self, league_code: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Charge toutes les données existantes pour une ligue"""
        
        # Matchs
        matches_file = os.path.join(self.matches_folder, f"{league_code}.csv")
        matches_df = pd.DataFrame()
        if os.path.exists(matches_file):
            try:
                matches_df = pd.read_csv(matches_file)
                # Conversion de la colonne date
                matches_df['date'] = pd.to_datetime(matches_df['date']).dt.date
            except Exception as e:
                logger.error(f"❌ Erreur chargement matchs {league_code}: {e}")
        
        # Stats joueurs
        stats_file = os.path.join(self.player_stats_folder, f"{league_code}_players.csv")
        stats_df = pd.DataFrame()
        if os.path.exists(stats_file):
            try:
                stats_df = pd.read_csv(stats_file)
                stats_df['match_date'] = pd.to_datetime(stats_df['match_date']).dt.date
            except Exception as e:
                logger.error(f"❌ Erreur chargement stats joueurs {league_code}: {e}")
        
        # Compositions
        lineups_file = os.path.join(self.match_lineups_folder, f"{league_code}_lineups.csv")
        lineups_df = pd.DataFrame()
        if os.path.exists(lineups_file):
            try:
                lineups_df = pd.read_csv(lineups_file)
                lineups_df['match_date'] = pd.to_datetime(lineups_df['match_date']).dt.date
            except Exception as e:
                logger.error(f"❌ Erreur chargement compositions {league_code}: {e}")
        
        # Effectifs
        rosters_file = os.path.join(self.team_rosters_folder, f"{league_code}_rosters.csv")
        rosters_df = pd.DataFrame()
        if os.path.exists(rosters_file):
            try:
                rosters_df = pd.read_csv(rosters_file)
            except Exception as e:
                logger.error(f"❌ Erreur chargement effectifs {league_code}: {e}")
        
        return matches_df, stats_df, lineups_df, rosters_df
    
    def filter_recent_matches(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """Filtre les matchs récents qui nécessitent une mise à jour des stats joueurs"""
        if matches_df.empty:
            return matches_df
        
        # Filtrer par date (dernière semaine) et statut terminé
        recent_finished = matches_df[
            (matches_df['date'] >= self.update_from) & 
            (matches_df['status_short'] == 'FT')
        ].copy()
        
        return recent_finished
    
    def get_fixture_players(self, fixture_id: int) -> Optional[Dict]:
        """Récupère les stats des joueurs pour un match"""
        params = {'fixture': fixture_id}
        data = self.make_api_request('fixtures/players', params)
        
        if data and 'response' in data:
            return data['response']
        return None
    
    def process_player_stats(self, player_data: Dict, fixture_id: int, 
                           league_code: str, match_date: str) -> List[Dict]:
        """Traite les données d'un joueur pour un match (même logique que le collecteur initial)"""
        processed_stats = []
        
        team_info = player_data.get('team', {})
        players = player_data.get('players', [])
        
        for player_info in players:
            player = player_info.get('player', {})
            stats_list = player_info.get('statistics', [])
            
            if not stats_list:
                continue
                
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
    
    def update_league_players(self, league_code: str) -> None:
        """Met à jour les données joueurs pour une ligue"""
        logger.info(f"🏆 Mise à jour joueurs pour {league_code} ({self.leagues[league_code]})")
        
        # Charger les données existantes
        matches_df, existing_stats_df, existing_lineups_df, existing_rosters_df = self.load_existing_data(league_code)
        
        if matches_df.empty:
            logger.warning(f"❌ Aucun match trouvé pour {league_code}")
            return
        
        logger.info(f"📂 Données existantes: {len(matches_df)} matchs, {len(existing_stats_df)} stats joueurs")
        
        # Identifier les matchs récents à traiter
        recent_matches = self.filter_recent_matches(matches_df)
        
        if recent_matches.empty:
            logger.info(f"✅ Aucun nouveau match récent pour {league_code}")
            return
        
        logger.info(f"⚽ {len(recent_matches)} nouveaux matchs récents à traiter")
        
        # Identifier les matchs qui n'ont pas encore de stats joueurs
        existing_fixture_ids = set()
        if not existing_stats_df.empty:
            existing_fixture_ids = set(existing_stats_df['fixture_id'].unique())
        
        new_matches_for_players = recent_matches[
            ~recent_matches['fixture_id'].isin(existing_fixture_ids)
        ]
        
        if new_matches_for_players.empty:
            logger.info(f"✅ Stats joueurs déjà à jour pour {league_code}")
            return
        
        logger.info(f"🆕 {len(new_matches_for_players)} matchs nécessitent des stats joueurs")
        
        # Collecte des nouvelles stats
        new_stats = []
        new_lineups = []
        new_teams = {}
        
        for _, match in new_matches_for_players.iterrows():
            fixture_id = match['fixture_id']
            match_date = match['date'].strftime('%Y-%m-%d')
            
            logger.info(f"⚽ Traitement match {fixture_id}")
            
            # Récupération des stats joueurs
            players_data = self.get_fixture_players(fixture_id)
            
            if not players_data:
                logger.warning(f"⚠️ Pas de données joueurs pour match {fixture_id}")
                continue
            
            # Traitement des données
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
                
                # Stats individuelles
                player_stats = self.process_player_stats(
                    team_data, fixture_id, league_code, match_date
                )
                new_stats.extend(player_stats)
                
                # Composition d'équipe
                team_composition = {
                    'team_id': team_id,
                    'team_name': team_name,
                    'players_count': len(team_data.get('players', []))
                }
                match_lineup['teams'].append(team_composition)
                
                # Effectifs
                if team_id not in new_teams:
                    new_teams[team_id] = {
                        'team_id': team_id,
                        'team_name': team_name,
                        'league_code': league_code,
                        'players': set()
                    }
                
                for player_info in team_data.get('players', []):
                    player = player_info.get('player', {})
                    new_teams[team_id]['players'].add((
                        player.get('id'),
                        player.get('name')
                    ))
            
            new_lineups.append(match_lineup)
            self.stats['new_matches_found'] += 1
            
            # Pause API
            time.sleep(0.5)
        
        # Mise à jour des données
        if new_stats:
            self.update_player_stats(existing_stats_df, new_stats, league_code)
            self.stats['new_player_stats'] += len(new_stats)
        
        if new_lineups:
            self.update_match_lineups(existing_lineups_df, new_lineups, league_code)
        
        if new_teams:
            self.update_team_rosters(existing_rosters_df, new_teams, league_code)
        
        self.stats['leagues_processed'] += 1
        logger.info(f"✅ {league_code} mis à jour - {len(new_stats)} nouvelles stats joueurs")
    
    def update_player_stats(self, existing_df: pd.DataFrame, new_stats: List[Dict], league_code: str) -> None:
        """Met à jour le fichier des stats joueurs"""
        new_df = pd.DataFrame(new_stats)
        
        if not existing_df.empty:
            # Supprimer les anciennes données (> 365 jours)
            existing_df['match_date'] = pd.to_datetime(existing_df['match_date']).dt.date
            recent_existing = existing_df[existing_df['match_date'] >= self.cutoff_date]
            
            if len(recent_existing) != len(existing_df):
                removed = len(existing_df) - len(recent_existing)
                logger.info(f"🗑️ Suppression de {removed} stats joueurs anciennes")
            
            # Combiner avec les nouvelles données
            combined_df = pd.concat([recent_existing, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Sauvegarder
        filepath = os.path.join(self.player_stats_folder, f"{league_code}_players.csv")
        try:
            combined_df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Stats joueurs mises à jour: {filepath} ({len(combined_df)} lignes)")
            self.stats['files_updated'] += 1
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde stats joueurs {league_code}: {e}")
    
    def update_match_lineups(self, existing_df: pd.DataFrame, new_lineups: List[Dict], league_code: str) -> None:
        """Met à jour le fichier des compositions"""
        # Aplatir les nouvelles compositions
        flattened_lineups = []
        for lineup in new_lineups:
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
                if i == 0:
                    flattened_lineups.append(team_info)
                else:
                    if flattened_lineups:
                        flattened_lineups[-1].update({
                            f'team_{i+1}_id': team['team_id'],
                            f'team_{i+1}_name': team['team_name'],
                            f'team_{i+1}_players_count': team['players_count']
                        })
        
        new_df = pd.DataFrame(flattened_lineups)
        
        if not existing_df.empty:
            # Supprimer les anciennes données
            existing_df['match_date'] = pd.to_datetime(existing_df['match_date']).dt.date
            recent_existing = existing_df[existing_df['match_date'] >= self.cutoff_date]
            
            combined_df = pd.concat([recent_existing, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Sauvegarder
        filepath = os.path.join(self.match_lineups_folder, f"{league_code}_lineups.csv")
        try:
            combined_df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Compositions mises à jour: {filepath} ({len(combined_df)} matchs)")
            self.stats['files_updated'] += 1
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde compositions {league_code}: {e}")
    
    def update_team_rosters(self, existing_df: pd.DataFrame, new_teams: Dict, league_code: str) -> None:
        """Met à jour le fichier des effectifs d'équipes"""
        new_rosters = []
        for team_id, team_info in new_teams.items():
            for player_id, player_name in team_info['players']:
                new_rosters.append({
                    'league_code': league_code,
                    'team_id': team_id,
                    'team_name': team_info['team_name'],
                    'player_id': player_id,
                    'player_name': player_name
                })
        
        new_df = pd.DataFrame(new_rosters)
        
        if not existing_df.empty:
            # Pour les effectifs, on garde une liste unique de joueurs par équipe
            # Combiner et dédupliquer
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            # Supprimer les doublons (même joueur, même équipe)
            combined_df = combined_df.drop_duplicates(subset=['team_id', 'player_id'], keep='last')
        else:
            combined_df = new_df
        
        # Sauvegarder
        filepath = os.path.join(self.team_rosters_folder, f"{league_code}_rosters.csv")
        try:
            combined_df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Effectifs mis à jour: {filepath} ({len(combined_df)} joueurs)")
            self.stats['files_updated'] += 1
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde effectifs {league_code}: {e}")
    
    def run_incremental_update(self) -> None:
        """Lance la mise à jour incrémentale pour toutes les ligues"""
        logger.info("🚀 === DÉBUT DE LA MISE À JOUR INCRÉMENTALE JOUEURS ===")
        logger.info(f"📅 Période de mise à jour: {self.update_from} à {self.today}")
        logger.info(f"🏆 Ligues à traiter: {list(self.leagues.keys())}")
        
        start_time = datetime.now()
        
        for league_code in self.leagues.keys():
            try:
                logger.info(f"\n🏟️ --- Mise à jour joueurs {league_code} ---")
                self.update_league_players(league_code)
                
                # Pause entre les ligues
                logger.info("⏱️ Pause de 5 secondes...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de la mise à jour joueurs {league_code}: {e}")
                continue
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Résumé final
        logger.info(f"\n🎉 === MISE À JOUR JOUEURS TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"✅ Ligues traitées: {self.stats['leagues_processed']}/{len(self.leagues)}")
        logger.info(f"🆕 Nouveaux matchs traités: {self.stats['new_matches_found']}")
        logger.info(f"🏃 Nouvelles stats joueurs: {self.stats['new_player_stats']}")
        logger.info(f"📁 Fichiers mis à jour: {self.stats['files_updated']}")
        logger.info(f"🌐 Requêtes API: {self.stats['api_calls']}")
        logger.info(f"❌ Requêtes échouées: {self.stats['failed_requests']}")
        logger.info(f"📁 Fenêtre de données maintenue: 365 derniers jours")
        
        # Résumé des fichiers par type
        logger.info(f"\n📊 === RÉSUMÉ DES DONNÉES ===")
        
        for folder_name, folder_path in [
            ("Stats joueurs", self.player_stats_folder),
            ("Compositions", self.match_lineups_folder), 
            ("Effectifs", self.team_rosters_folder)
        ]:
            if os.path.exists(folder_path):
                csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
                total_size = 0
                total_records = 0
                
                for csv_file in csv_files:
                    file_path = os.path.join(folder_path, csv_file)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        
                        # Compter les lignes
                        df = pd.read_csv(file_path)
                        total_records += len(df)
                    except:
                        pass
                
                size_mb = total_size / (1024 * 1024)
                logger.info(f"📊 {folder_name}: {len(csv_files)} fichiers, {total_records} enregistrements, {size_mb:.2f} MB")

def main():
    """Fonction principale"""
    import os
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        return
    
    logger.info("✅ Clé API récupérée depuis les variables d'environnement")
    
    # Création de l'updater et lancement
    updater = FootballPlayersUpdater(RAPIDAPI_KEY)
    updater.run_incremental_update()

if __name__ == "__main__":
    main()
