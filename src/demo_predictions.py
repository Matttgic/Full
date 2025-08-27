#!/usr/bin/env python3
"""
Version démonstration du système de prédictions
Utilise les données existantes sans appel API pour montrer le fonctionnement
"""

import pandas as pd
import numpy as np
import os
import glob
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import random

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo_predictions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DemoPredictionsWorkflow:
    """
    Version démonstration du workflow de prédictions
    Utilise les données existantes et simule des matchs du jour
    """
    
    def __init__(self):
        """Initialise le workflow de démonstration"""
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
        
        self.SIMILARITY_THRESHOLD = 0.15
        self.MIN_BOOKMAKERS_THRESHOLD = 2
        
        self.odds_data_dir = 'data/odds/raw_data'
        self.predictions_dir = 'data/predictions'
        os.makedirs(self.predictions_dir, exist_ok=True)
        
        self.today = date.today()
        
        # Charger les données historiques
        logger.info("🔄 Chargement des données historiques existantes...")
        self.historical_odds_data = self.load_all_historical_odds()
        self.historical_feature_matrix = self.create_comprehensive_feature_matrix()
        logger.info(f"✅ Données historiques chargées: {len(self.historical_feature_matrix)} matchs")

    def load_all_historical_odds(self) -> pd.DataFrame:
        """Charge toutes les données de cotes historiques disponibles"""
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
        """Crée une matrice de caractéristiques complète"""
        if self.historical_odds_data.empty:
            return pd.DataFrame()
        
        df = self.historical_odds_data.copy()
        df['odd'] = pd.to_numeric(df['odd'], errors='coerce')
        df.dropna(subset=['odd'], inplace=True)
        
        # === FILTRAGE DES TYPES DE PARIS ===
        # On ne garde que les types de paris demandés pour l'analyse
        allowed_bet_types = [
            'Match Winner',       # Pour 1X2
            'Both Teams Score',   # Pour BTTS
            'Goals Over/Under'    # Pour Over/Under
        ]
        df = df[df['bet_type_name'].isin(allowed_bet_types)]

        if df.empty:
            logger.warning("Aucun des types de paris autorisés n'a été trouvé dans les données historiques.")
            return pd.DataFrame()

        logger.info(f"Paris filtrés. Gardés: {df['bet_type_name'].nunique()} types de paris principaux.")

        df['bet_identifier'] = df['bet_type_name'].astype(str) + '_' + df['bet_value'].astype(str)
        
        # Filtrer les paris fiables
        bookmaker_counts = df.groupby(['fixture_id', 'bet_identifier'])['bookmaker_id'].nunique().reset_index()
        reliable_bets = bookmaker_counts[bookmaker_counts['bookmaker_id'] >= self.MIN_BOOKMAKERS_THRESHOLD]
        
        if reliable_bets.empty:
            logger.warning("Aucun pari fiable trouvé")
            return pd.DataFrame()
        
        reliable_df = pd.merge(df, reliable_bets[['fixture_id', 'bet_identifier']], 
                              on=['fixture_id', 'bet_identifier'])
        
        mean_odds = reliable_df.groupby(['fixture_id', 'bet_identifier'])['odd'].mean().reset_index()
        feature_matrix = mean_odds.pivot(index='fixture_id', columns='bet_identifier', values='odd')
        
        logger.info(f"✅ Matrice créée: {feature_matrix.shape[0]} matchs, {feature_matrix.shape[1]} types de paris")
        return feature_matrix

    def simulate_today_fixtures(self) -> List[Dict]:
        """Simule des matchs du jour basés sur les équipes des données existantes"""
        logger.info("🎭 Simulation des matchs du jour...")
        
        # Récupérer des équipes réelles des données historiques
        matches_dir = 'data/matches'
        team_pool = []
        
        for league_code in ['ENG1', 'FRA1', 'ITA1', 'GER1', 'SPA1']:
            match_file = os.path.join(matches_dir, f"{league_code}.csv")
            if os.path.exists(match_file):
                try:
                    df = pd.read_csv(match_file)
                    if 'home_team_name' in df.columns and 'away_team_name' in df.columns:
                        home_teams = df['home_team_name'].dropna().unique()
                        away_teams = df['away_team_name'].dropna().unique()
                        
                        for team in list(home_teams)[:5]:  # 5 équipes par ligue
                            team_pool.append({
                                'name': team,
                                'league_code': league_code,
                                'league_name': self.all_leagues[league_code]['name'],
                                'country': self.all_leagues[league_code]['country']
                            })
                except Exception as e:
                    logger.warning(f"Erreur lecture équipes {league_code}: {e}")
        
        # Créer des matchs simulés
        simulated_fixtures = []
        fixture_id_base = 9000000  # ID de base pour éviter conflits
        
        for i in range(8):  # 8 matchs simulés
            # Sélectionner deux équipes de la même ligue
            league_teams = [t for t in team_pool if t['league_code'] == random.choice(['ENG1', 'FRA1', 'ITA1', 'GER1', 'SPA1'])]
            if len(league_teams) >= 2:
                home_team, away_team = random.sample(league_teams, 2)
                
                fixture = {
                    'fixture': {
                        'id': fixture_id_base + i,
                        'date': f"{self.today}T{random.randint(15, 21):02d}:00:00+00:00",
                        'status': {'long': 'Not Started', 'short': 'NS'},
                        'venue': {'name': f"Stadium {i+1}", 'city': home_team['country']}
                    },
                    'league': {
                        'id': self.all_leagues[home_team['league_code']]['id'],
                        'name': home_team['league_name'],
                        'season': 2024
                    },
                    'teams': {
                        'home': {'id': 1000 + i, 'name': home_team['name']},
                        'away': {'id': 2000 + i, 'name': away_team['name']}
                    },
                    'league_code': home_team['league_code'],
                    'league_name': home_team['league_name'],
                    'country': home_team['country']
                }
                
                simulated_fixtures.append(fixture)
        
        logger.info(f"🎯 {len(simulated_fixtures)} matchs simulés créés")
        return simulated_fixtures

    def simulate_fixture_odds(self, fixture_id: int) -> Dict:
        """Simule des cotes réalistes pour un match basées sur les données historiques"""
        if self.historical_feature_matrix.empty:
            return {}
        
        # Sélectionner un match historique aléatoire comme base
        random_match_idx = random.choice(self.historical_feature_matrix.index)
        historical_odds = self.historical_feature_matrix.loc[random_match_idx].dropna()
        
        # Ajouter un peu de variation aux cotes (+/- 10%)
        simulated_odds = {}
        for bet_identifier, odd in historical_odds.items():
            variation = random.uniform(0.9, 1.1)
            simulated_odd = round(odd * variation, 2)
            if simulated_odd > 0:  # Vérifier que la cote est positive
                simulated_odds[bet_identifier] = simulated_odd
        
        return simulated_odds

    def calculate_similarity_for_all_bets(self, target_odds: Dict) -> Dict:
        """Calcule le pourcentage de similarité pour tous les types de paris"""
        if not target_odds or self.historical_feature_matrix.empty:
            return {}
        
        similarity_results = {}
        
        for bet_identifier, target_odd in target_odds.items():
            if bet_identifier in self.historical_feature_matrix.columns:
                historical_odds = self.historical_feature_matrix[bet_identifier].dropna()
                
                if len(historical_odds) < 10:
                    continue
                
                distances = np.abs(historical_odds - target_odd)
                similar_matches = distances[distances <= self.SIMILARITY_THRESHOLD]
                
                if len(similar_matches) > 0:
                    similarity_percentage = (len(similar_matches) / len(historical_odds)) * 100
                    avg_distance = similar_matches.mean()
                    
                    similarity_results[bet_identifier] = {
                        'similarity_percentage': round(similarity_percentage, 2),
                        'similar_matches_count': len(similar_matches),
                        'total_historical_matches': len(historical_odds),
                        'avg_distance': round(avg_distance, 4),
                        'target_odd': target_odd,
                        'confidence_score': min(100, (len(similar_matches) / 50) * 100)
                    }
        
        return similarity_results

    def create_demo_predictions_csv(self, fixtures_data: List[Dict]) -> Tuple[str, str]:
        """Crée les fichiers CSV de démonstration"""
        daily_filename = f"demo_daily_{self.today.strftime('%Y-%m-%d')}.csv"
        daily_filepath = os.path.join(self.predictions_dir, daily_filename)
        demo_historical_filepath = os.path.join(self.predictions_dir, "demo_historical_predictions.csv")
        
        all_predictions = []
        
        for fixture_data in fixtures_data:
            fixture_id = fixture_data.get('fixture', {}).get('id')
            fixture_info = fixture_data.get('fixture', {})
            teams_info = fixture_data.get('teams', {})
            league_info = fixture_data.get('league', {})
            
            logger.info(f"⚽ Analyse match {fixture_id}: {teams_info.get('home', {}).get('name')} vs {teams_info.get('away', {}).get('name')}")
            
            # Simuler les cotes actuelles
            target_odds = self.simulate_fixture_odds(fixture_id)
            if not target_odds:
                logger.warning(f"Impossible de simuler les cotes pour {fixture_id}")
                continue
            
            # Calculer les similarités
            similarities = self.calculate_similarity_for_all_bets(target_odds)
            
            # Préparer les données de base
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
                'total_bet_types_analyzed': len(similarities),
                'analysis_timestamp': datetime.now().isoformat(),
                'demo_mode': True
            }
            
            # Ajouter les données de similarité
            prediction_row = base_data.copy()
            
            for bet_identifier, sim_data in similarities.items():
                clean_bet_name = bet_identifier.replace(' ', '_').replace('/', '_').replace('-', '_')
                
                prediction_row.update({
                    f"{clean_bet_name}_target_odd": sim_data['target_odd'],
                    f"{clean_bet_name}_similarity_pct": sim_data['similarity_percentage'],
                    f"{clean_bet_name}_similar_matches": sim_data['similar_matches_count'],
                    f"{clean_bet_name}_confidence": sim_data['confidence_score']
                })
            
            all_predictions.append(prediction_row)
        
        if not all_predictions:
            logger.warning("Aucune prédiction générée")
            return "", ""
        
        # Créer DataFrame
        predictions_df = pd.DataFrame(all_predictions)
        
        # Sauvegarder CSV quotidien
        predictions_df.to_csv(daily_filepath, index=False, encoding='utf-8')
        logger.info(f"💾 CSV quotidien de démo sauvegardé: {daily_filepath} ({len(predictions_df)} matchs)")
        
        # Ajouter au CSV historique de démo
        if os.path.exists(demo_historical_filepath):
            historical_df = pd.read_csv(demo_historical_filepath)
            combined_df = pd.concat([historical_df, predictions_df], ignore_index=True)
        else:
            combined_df = predictions_df
        
        combined_df.to_csv(demo_historical_filepath, index=False, encoding='utf-8')
        logger.info(f"📚 CSV historique de démo mis à jour: {demo_historical_filepath} ({len(combined_df)} entrées totales)")
        
        return daily_filepath, demo_historical_filepath

    def run_demo_workflow(self):
        """Lance le workflow de démonstration complet"""
        logger.info("🎭 === DÉBUT DU WORKFLOW DÉMONSTRATION ===")
        start_time = datetime.now()
        
        try:
            if self.historical_odds_data.empty:
                logger.error("❌ Aucune donnée historique disponible pour la démonstration")
                logger.info("💡 Assurez-vous que les fichiers de cotes existent dans data/odds/raw_data/")
                return
            
            # 1. Simuler les matchs du jour
            simulated_fixtures = self.simulate_today_fixtures()
            
            if not simulated_fixtures:
                logger.error("❌ Impossible de simuler des matchs")
                return
            
            # 2. Analyser et créer les prédictions
            daily_file, historical_file = self.create_demo_predictions_csv(simulated_fixtures)
            
            # 3. Résumé avec statistiques intéressantes
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"\n🎉 === DÉMONSTRATION TERMINÉE ===")
            logger.info(f"⏱️ Durée: {duration}")
            logger.info(f"📊 Matchs simulés: {len(simulated_fixtures)}")
            logger.info(f"📁 Fichier quotidien: {daily_file}")
            logger.info(f"📚 Fichier historique: {historical_file}")
            logger.info(f"🔢 Données historiques utilisées: {len(self.historical_odds_data)} cotes")
            logger.info(f"🎯 Types de paris analysés: {self.historical_feature_matrix.shape[1]}")
            
            # Afficher quelques résultats intéressants
            if daily_file and os.path.exists(daily_file):
                df = pd.read_csv(daily_file)
                similarity_cols = [col for col in df.columns if col.endswith('_similarity_pct')]
                if similarity_cols:
                    # Trouver les prédictions les plus fiables
                    high_confidence_bets = []
                    for col in similarity_cols[:5]:  # Top 5 types de paris
                        max_similarity = df[col].max()
                        if pd.notna(max_similarity) and max_similarity > 50:
                            bet_type = col.replace('_similarity_pct', '')
                            high_confidence_bets.append(f"{bet_type}: {max_similarity:.1f}%")
                    
                    if high_confidence_bets:
                        logger.info("🔥 Meilleures prédictions:")
                        for bet in high_confidence_bets:
                            logger.info(f"   • {bet}")
            
        except Exception as e:
            logger.error(f"❌ Erreur dans le workflow de démonstration: {e}", exc_info=True)

def main():
    """Point d'entrée principal"""
    logger.info("🎭 === MODE DÉMONSTRATION SYSTÈME DE PRÉDICTIONS ===")
    logger.info("ℹ️ Ce mode utilise les données existantes sans appel API")
    
    # Lancer le workflow de démonstration
    workflow = DemoPredictionsWorkflow()
    workflow.run_demo_workflow()

if __name__ == "__main__":
    main()
