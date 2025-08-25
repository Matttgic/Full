"""
Ce script génère des prédictions quotidiennes en se basant sur la similarité
des cotes par rapport à un historique de matchs.

Rôle :
- Récupère les matchs du jour pour les ligues configurées.
- Pour chaque match, récupère les cotes actuelles pour différents types de paris.
- Compare ces cotes à une base de données historique de matchs (`data/odds/`).
- Calcule un "pourcentage de similarité" qui indique la fréquence à laquelle
  des cotes similaires ont été observées dans le passé.
- Applique des seuils de robustesse pour éviter les prédictions basées sur
  des données insuffisantes (ex: `MIN_SIMILAR_MATCHES_THRESHOLD`).
- Sauvegarde les résultats dans des fichiers CSV quotidien et historique.

Ce workflow offre une approche de prédiction alternative, complémentaire au modèle Elo.
"""
import pandas as pd
import numpy as np
import os
import glob
import json
import requests
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import time
from src.config import MIN_SIMILAR_MATCHES_THRESHOLD, SIMILARITY_THRESHOLD, MIN_BOOKMAKERS_THRESHOLD

# Configuration du logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_predictions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyPredictionsWorkflow:
    """
    Workflow quotidien de prédictions de matchs de football.
    Génère un CSV quotidien et historique avec % de similarité pour tous types de paris.
    """
    
    def __init__(self, rapidapi_key: str):
        """
        Initialise le workflow avec la clé RapidAPI
        """
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration des ligues (même que les autres scripts)
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
        
        # Configuration des seuils depuis le fichier config.py
        self.SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLD
        self.MIN_BOOKMAKERS_THRESHOLD = MIN_BOOKMAKERS_THRESHOLD
        self.MIN_SIMILAR_MATCHES_THRESHOLD = MIN_SIMILAR_MATCHES_THRESHOLD
        
        # Dossiers
        self.odds_data_dir = 'data/odds/raw_data'
        self.predictions_dir = 'data/predictions'
        os.makedirs(self.predictions_dir, exist_ok=True)
        
        # Date du jour
        self.today = date.today()
        
        # Charger les données historiques une fois
        logger.info("🔄 Chargement des données historiques des 15 ligues...")
        self.historical_odds_data = self.load_all_historical_odds()
        self.historical_feature_matrix = self.create_comprehensive_feature_matrix()
        logger.info(f"✅ Données historiques chargées: {len(self.historical_feature_matrix)} matchs")

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Effectue une requête à l'API avec gestion des erreurs"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(3):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
                logger.warning(f"API error {response.status_code}: {response.text[:200]}")
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                time.sleep(2)
        return None

    def load_all_historical_odds(self) -> pd.DataFrame:
        """Charge toutes les données de cotes historiques des 15 ligues"""
        all_odds = []
        
        for league_code in self.all_leagues.keys():
            odds_file = os.path.join(self.odds_data_dir, f"{league_code}_complete_odds.csv")
            if os.path.exists(odds_file):
                try:
                    df = pd.read_csv(odds_file)
                    df['league_code'] = league_code
                    all_odds.append(df)
                    logger.info(f"📂 {league_code}: {len(df)} cotes chargées")
                except Exception as e:
                    logger.warning(f"Erreur lecture {league_code}: {e}")
        
        if all_odds:
            combined_df = pd.concat(all_odds, ignore_index=True)
            logger.info(f"📊 Total cotes historiques: {len(combined_df)}")
            return combined_df
        return pd.DataFrame()

    def create_comprehensive_feature_matrix(self) -> pd.DataFrame:
        """
        Crée une matrice de caractéristiques complète pour TOUS les types de paris
        """
        if self.historical_odds_data.empty:
            return pd.DataFrame()
        
        # Nettoyage des données
        df = self.historical_odds_data.copy()
        df['odd'] = pd.to_numeric(df['odd'], errors='coerce')
        df.dropna(subset=['odd'], inplace=True)
        
        # Créer un identifiant unique pour chaque type de pari + valeur
        df['bet_identifier'] = df['bet_type_name'].astype(str) + '_' + df['bet_value'].astype(str)
        
        # Filtrer les paris avec suffisamment de bookmakers
        bookmaker_counts = df.groupby(['fixture_id', 'bet_identifier'])['bookmaker_id'].nunique().reset_index()
        reliable_bets = bookmaker_counts[
            bookmaker_counts['bookmaker_id'] >= self.MIN_BOOKMAKERS_THRESHOLD
        ]
        
        if reliable_bets.empty:
            logger.warning("Aucun pari fiable trouvé")
            return pd.DataFrame()
        
        # Joindre avec les données fiables
        reliable_df = pd.merge(
            df, 
            reliable_bets[['fixture_id', 'bet_identifier']], 
            on=['fixture_id', 'bet_identifier']
        )
        
        # Calculer les cotes moyennes par fixture et type de pari
        mean_odds = reliable_df.groupby(['fixture_id', 'bet_identifier'])['odd'].mean().reset_index()
        
        # Créer la matrice pivot
        feature_matrix = mean_odds.pivot(
            index='fixture_id', 
            columns='bet_identifier', 
            values='odd'
        )
        
        logger.info(f"✅ Matrice créée: {feature_matrix.shape[0]} matchs, {feature_matrix.shape[1]} types de paris")
        return feature_matrix

    def get_today_fixtures(self) -> List[Dict]:
        """Récupère tous les matchs du jour pour toutes les ligues"""
        today_str = self.today.strftime('%Y-%m-%d')
        logger.info(f"🔍 Recherche des matchs du {today_str}")
        
        all_fixtures = []
        
        for league_code, league_info in self.all_leagues.items():
            logger.info(f"🏆 Récupération {league_code} - {league_info['name']}")
            
            # Essayer différentes saisons
            for season in [2024, 2025]:
                params = {
                    'league': league_info['id'],
                    'season': season,
                    'date': today_str
                }
                
                data = self.make_api_request('fixtures', params)
                if data and 'response' in data:
                    season_fixtures = data['response']
                    
                    for fixture in season_fixtures:
                        fixture['league_code'] = league_code
                        fixture['league_name'] = league_info['name']
                        fixture['country'] = league_info['country']
                    
                    all_fixtures.extend(season_fixtures)
                    logger.info(f"📅 {league_code} saison {season}: {len(season_fixtures)} matchs")
                
                time.sleep(0.5)  # Respecter les limites API
        
        logger.info(f"📊 Total matchs du jour: {len(all_fixtures)}")
        return all_fixtures

    def get_fixture_odds(self, fixture_id: int) -> Optional[Dict]:
        """Récupère les cotes pour un match spécifique"""
        params = {'fixture': fixture_id}
        data = self.make_api_request('odds', params)
        return data['response'] if data and 'response' in data else None

    def process_fixture_odds(self, fixture_id: int, odds_data: List[Dict]) -> Dict:
        """Traite les cotes d'un match et crée un vecteur de caractéristiques"""
        if not odds_data:
            return {}
        
        processed_odds = []
        
        for odds_entry in odds_data:
            for bookmaker in odds_entry.get('bookmakers', []):
                for bet in bookmaker.get('bets', []):
                    for value in bet.get('values', []):
                        processed_odds.append({
                            'fixture_id': fixture_id,
                            'bet_type_name': bet.get('name'),
                            'bet_value': value.get('value'),
                            'odd': value.get('odd'),
                            'bookmaker_id': bookmaker.get('id')
                        })
        
        if not processed_odds:
            return {}
        
        # Créer DataFrame et traiter comme les données historiques
        df = pd.DataFrame(processed_odds)
        df['odd'] = pd.to_numeric(df['odd'], errors='coerce')
        df.dropna(subset=['odd'], inplace=True)
        
        df['bet_identifier'] = df['bet_type_name'].astype(str) + '_' + df['bet_value'].astype(str)
        
        # Calculer cotes moyennes
        mean_odds = df.groupby('bet_identifier')['odd'].mean()
        
        return mean_odds.to_dict()

    def calculate_similarity_for_all_bets(self, target_odds: Dict) -> Dict:
        """
        Calcule le pourcentage de similarité pour tous les types de paris
        """
        if not target_odds or self.historical_feature_matrix.empty:
            return {}
        
        similarity_results = {}
        
        for bet_identifier, target_odd in target_odds.items():
            if bet_identifier in self.historical_feature_matrix.columns:
                # Récupérer les cotes historiques pour ce type de pari
                historical_odds = self.historical_feature_matrix[bet_identifier].dropna()
                
                if len(historical_odds) < self.MIN_SIMILAR_MATCHES_THRESHOLD:
                    logger.debug(f"Pas assez de données pour {bet_identifier}: {len(historical_odds)} matchs < {self.MIN_SIMILAR_MATCHES_THRESHOLD}")
                    continue
                
                # Calculer les distances (différences absolues)
                distances = np.abs(historical_odds - target_odd)
                
                # Trouver les matchs similaires
                similar_matches = distances[distances <= self.SIMILARITY_THRESHOLD]
                
                # Appliquer le seuil de matchs similaires
                if len(similar_matches) >= self.MIN_SIMILAR_MATCHES_THRESHOLD:
                    # Calculer le pourcentage de similarité
                    similarity_percentage = (len(similar_matches) / len(historical_odds)) * 100
                    avg_distance = similar_matches.mean()
                    
                    similarity_results[bet_identifier] = {
                        'similarity_percentage': round(similarity_percentage, 2),
                        'similar_matches_count': len(similar_matches),
                        'total_historical_matches': len(historical_odds),
                        'avg_distance': round(avg_distance, 4),
                        'target_odd': target_odd,
                        'similarity_reference_count': len(similar_matches)
                    }
        
        return similarity_results

    def create_daily_predictions_csv(self, fixtures_data: List[Dict]) -> Tuple[str, str]:
        """
        Crée les fichiers CSV quotidien et historique
        """
        daily_filename = f"daily_{self.today.strftime('%Y-%m-%d')}.csv"
        daily_filepath = os.path.join(self.predictions_dir, daily_filename)
        historical_filepath = os.path.join(self.predictions_dir, "historical_predictions.csv")
        
        all_long_format_predictions = []
        
        for fixture_data in fixtures_data:
            fixture_id = fixture_data.get('fixture', {}).get('id')
            fixture_info = fixture_data.get('fixture', {})
            teams_info = fixture_data.get('teams', {})
            league_info = fixture_data.get('league', {})
            
            logger.info(f"⚽ Analyse match {fixture_id}: {teams_info.get('home', {}).get('name')} vs {teams_info.get('away', {}).get('name')}")
            
            # Récupérer les cotes actuelles
            odds_data = self.get_fixture_odds(fixture_id)
            if not odds_data:
                logger.warning(f"Pas de cotes pour le match {fixture_id}")
                continue
            
            # Traiter les cotes
            target_odds = self.process_fixture_odds(fixture_id, odds_data)
            if not target_odds:
                logger.warning(f"Impossible de traiter les cotes pour {fixture_id}")
                continue
            
            # Calculer les similarités
            similarities = self.calculate_similarity_for_all_bets(target_odds)
            
            base_data = {
                'date': self.today.strftime('%Y-%m-%d'),
                'match_time': fixture_info.get('date', ''),
                'fixture_id': fixture_id,
                'league_code': fixture_data.get('league_code', ''),
                'league_name': league_info.get('name', ''),
                'country': fixture_data.get('country', ''),
                'home_team': teams_info.get('home', {}).get('name', ''),
                'away_team': teams_info.get('away', {}).get('name', ''),
                'venue': fixture_info.get('venue', {}).get('name', ''),
                'status': fixture_info.get('status', {}).get('long', ''),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            if not similarities:
                row = base_data.copy()
                row['bet_type'] = "NO_BETS"
                all_long_format_predictions.append(row)
            else:
                for bet_identifier, sim_data in similarities.items():
                    bet_type, bet_value = bet_identifier.split('_', 1)
                    row = base_data.copy()
                    row.update({
                        'bet_type': bet_type,
                        'bet_value': bet_value,
                        'target_odd': sim_data['target_odd'],
                        'similarity_pct': sim_data['similarity_percentage'],
                        'similar_matches_count': sim_data['similar_matches_count'],
                        'similarity_reference_count': sim_data['similarity_reference_count']
                    })
                    all_long_format_predictions.append(row)

            time.sleep(1)  # Pause entre les appels API
        
        if not all_long_format_predictions:
            logger.warning("Aucune prédiction générée")
            return "", ""
        
        # Créer DataFrame
        predictions_df = pd.DataFrame(all_long_format_predictions)
        
        # Sauvegarder CSV quotidien
        predictions_df.to_csv(daily_filepath, index=False, encoding='utf-8')
        logger.info(f"💾 CSV quotidien sauvegardé: {daily_filepath} ({len(predictions_df)} matchs)")
        
        # Ajouter au CSV historique
        if os.path.exists(historical_filepath):
            # Charger l'historique existant et ajouter les nouvelles données
            historical_df = pd.read_csv(historical_filepath)
            combined_df = pd.concat([historical_df, predictions_df], ignore_index=True)
        else:
            combined_df = predictions_df
        
        # Sauvegarder l'historique
        combined_df.to_csv(historical_filepath, index=False, encoding='utf-8')
        logger.info(f"📚 CSV historique mis à jour: {historical_filepath} ({len(combined_df)} entrées totales)")
        
        return daily_filepath, historical_filepath

    def run_daily_workflow(self):
        """Lance le workflow quotidien complet"""
        logger.info("🚀 === DÉBUT DU WORKFLOW QUOTIDIEN DE PRÉDICTIONS ===")
        start_time = datetime.now()
        
        try:
            # 1. Récupérer les matchs du jour
            today_fixtures = self.get_today_fixtures()
            
            if not today_fixtures:
                logger.info("❌ Aucun match trouvé pour aujourd'hui")
                return
            
            # 2. Analyser et créer les prédictions
            daily_file, historical_file = self.create_daily_predictions_csv(today_fixtures)
            
            # 3. Résumé
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"\n🎉 === WORKFLOW TERMINÉ ===")
            logger.info(f"⏱️ Durée: {duration}")
            logger.info(f"📊 Matchs analysés: {len(today_fixtures)}")
            logger.info(f"📁 Fichier quotidien: {daily_file}")
            logger.info(f"📚 Fichier historique: {historical_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur dans le workflow: {e}", exc_info=True)

def main():
    """Point d'entrée principal"""
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        return
    
    logger.info("✅ Clé API récupérée")
    
    # Lancer le workflow
    workflow = DailyPredictionsWorkflow(RAPIDAPI_KEY)
    workflow.run_daily_workflow()

if __name__ == "__main__":
    main()