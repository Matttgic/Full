#!/usr/bin/env python3
"""
Analyseur des prédictions quotidiennes
Permet d'analyser les données historiques de prédictions
"""

import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime, date, timedelta
import logging
import argparse

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PredictionsAnalyzer:
    """
    Analyseur des prédictions de matchs de football
    """
    
    def __init__(self):
        self.predictions_dir = 'data/predictions'
        self.historical_file = os.path.join(self.predictions_dir, 'historical_predictions.csv')
        
    def load_historical_data(self) -> pd.DataFrame:
        """Charge les données historiques des prédictions"""
        if not os.path.exists(self.historical_file):
            logger.error(f"Fichier historique non trouvé: {self.historical_file}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.historical_file)
            logger.info(f"📚 Données historiques chargées: {len(df)} prédictions")
            return df
        except Exception as e:
            logger.error(f"Erreur lecture fichier historique: {e}")
            return pd.DataFrame()
    
    def analyze_by_league(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyse par ligue"""
        if df.empty:
            return pd.DataFrame()
        
        analysis = df.groupby('league_name').agg({
            'fixture_id': 'count',
            'total_bet_types_analyzed': 'mean'
        }).round(2)
        
        analysis.columns = ['matches_analyzed', 'avg_bet_types_per_match']
        analysis = analysis.sort_values('matches_analyzed', ascending=False)
        
        logger.info("\n📊 ANALYSE PAR LIGUE:")
        print(analysis.to_string())
        return analysis
    
    def analyze_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyse par date"""
        if df.empty:
            return pd.DataFrame()
        
        df['date'] = pd.to_datetime(df['date'])
        analysis = df.groupby('date').agg({
            'fixture_id': 'count',
            'total_bet_types_analyzed': 'mean'
        }).round(2)
        
        analysis.columns = ['matches_per_day', 'avg_bet_types']
        analysis = analysis.sort_values('date', ascending=False)
        
        logger.info("\n📅 ANALYSE PAR DATE:")
        print(analysis.tail(10).to_string())  # Derniers 10 jours
        return analysis
    
    def analyze_similarity_distribution(self, df: pd.DataFrame) -> Dict:
        """Analyse la distribution des pourcentages de similarité"""
        if df.empty:
            return {}
        
        # Identifier toutes les colonnes de similarité
        similarity_cols = [col for col in df.columns if col.endswith('_similarity_pct')]
        
        if not similarity_cols:
            logger.warning("Aucune colonne de similarité trouvée")
            return {}
        
        stats = {}
        
        for col in similarity_cols[:10]:  # Analyser les 10 premiers types de paris
            bet_type = col.replace('_similarity_pct', '')
            values = df[col].dropna()
            
            if len(values) > 0:
                stats[bet_type] = {
                    'count': len(values),
                    'mean': round(values.mean(), 2),
                    'std': round(values.std(), 2),
                    'min': round(values.min(), 2),
                    'max': round(values.max(), 2),
                    'median': round(values.median(), 2)
                }
        
        logger.info("\n🎯 DISTRIBUTION DES SIMILARITÉS (top 10 types de paris):")
        for bet_type, stat in stats.items():
            print(f"{bet_type[:30]:30} | Moy: {stat['mean']:5.1f}% | Med: {stat['median']:5.1f}% | Min-Max: {stat['min']:5.1f}%-{stat['max']:5.1f}% | Count: {stat['count']}")
        
        return stats
    
    def find_high_confidence_predictions(self, df: pd.DataFrame, min_confidence: float = 70.0) -> pd.DataFrame:
        """Trouve les prédictions avec haute confiance"""
        if df.empty:
            return pd.DataFrame()
        
        # Identifier les colonnes de confiance
        confidence_cols = [col for col in df.columns if col.endswith('_confidence')]
        
        if not confidence_cols:
            logger.warning("Aucune colonne de confiance trouvée")
            return pd.DataFrame()
        
        high_confidence_matches = []
        
        for _, row in df.iterrows():
            match_info = {
                'date': row['date'],
                'league': row['league_name'],
                'match': f"{row['home_team']} vs {row['away_team']}",
                'high_confidence_bets': []
            }
            
            for col in confidence_cols:
                if pd.notna(row[col]) and row[col] >= min_confidence:
                    bet_type = col.replace('_confidence', '')
                    similarity_col = f"{bet_type}_similarity_pct"
                    odd_col = f"{bet_type}_target_odd"
                    
                    match_info['high_confidence_bets'].append({
                        'bet_type': bet_type,
                        'confidence': row[col],
                        'similarity_pct': row.get(similarity_col, 'N/A'),
                        'target_odd': row.get(odd_col, 'N/A')
                    })
            
            if match_info['high_confidence_bets']:
                high_confidence_matches.append(match_info)
        
        logger.info(f"\n🔥 PRÉDICTIONS HAUTE CONFIANCE (≥{min_confidence}%):")
        for match in high_confidence_matches[:5]:  # Top 5
            print(f"\n{match['date']} | {match['league']} | {match['match']}")
            for bet in match['high_confidence_bets'][:3]:  # Top 3 paris par match
                print(f"  • {bet['bet_type'][:40]:40} | Conf: {bet['confidence']:5.1f}% | Sim: {bet['similarity_pct']:5.1f}% | Cote: {bet['target_odd']}")
        
        return pd.DataFrame(high_confidence_matches)
    
    def generate_daily_report(self, target_date: str = None) -> str:
        """Génère un rapport pour une date donnée"""
        if target_date is None:
            target_date = date.today().strftime('%Y-%m-%d')
        
        daily_file = os.path.join(self.predictions_dir, f"daily_{target_date}.csv")
        
        if not os.path.exists(daily_file):
            logger.error(f"Fichier quotidien non trouvé: {daily_file}")
            return ""
        
        try:
            df = pd.read_csv(daily_file)
            
            report = f"""
═══════════════════════════════════════
📊 RAPPORT QUOTIDIEN - {target_date}
═══════════════════════════════════════

📈 STATISTIQUES GÉNÉRALES:
• Nombre de matchs analysés: {len(df)}
• Ligues couvertes: {df['league_name'].nunique()}
• Types de paris moyens par match: {df['total_bet_types_analyzed'].mean():.1f}

🏆 LIGUES ANALYSÉES:
{df['league_name'].value_counts().to_string()}

⏰ HORAIRES DES MATCHS:
• Premier match: {df['match_time'].min()}
• Dernier match: {df['match_time'].max()}

🎯 PARIS HAUTE CONFIANCE (≥80%):
"""
            
            # Ajouter les paris haute confiance
            confidence_cols = [col for col in df.columns if col.endswith('_confidence')]
            high_conf_count = 0
            
            for col in confidence_cols:
                high_conf = df[df[col] >= 80.0]
                high_conf_count += len(high_conf)
            
            report += f"• Total paris haute confiance: {high_conf_count}\n"
            
            logger.info(report)
            return report
            
        except Exception as e:
            logger.error(f"Erreur génération rapport: {e}")
            return ""
    
    def export_filtered_data(self, df: pd.DataFrame, filters: Dict) -> str:
        """Exporte des données filtrées"""
        if df.empty:
            return ""
        
        filtered_df = df.copy()
        
        # Appliquer les filtres
        if 'league' in filters:
            filtered_df = filtered_df[filtered_df['league_name'].isin(filters['league'])]
        
        if 'date_from' in filters:
            filtered_df = filtered_df[filtered_df['date'] >= filters['date_from']]
        
        if 'date_to' in filters:
            filtered_df = filtered_df[filtered_df['date'] <= filters['date_to']]
        
        # Nom du fichier de sortie
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(self.predictions_dir, f"filtered_export_{timestamp}.csv")
        
        # Exporter
        filtered_df.to_csv(output_file, index=False)
        logger.info(f"💾 Données filtrées exportées: {output_file} ({len(filtered_df)} lignes)")
        
        return output_file
    
    def run_complete_analysis(self):
        """Lance une analyse complète"""
        logger.info("🚀 === ANALYSE COMPLÈTE DES PRÉDICTIONS ===")
        
        # Charger les données
        df = self.load_historical_data()
        if df.empty:
            return
        
        # Analyses
        self.analyze_by_league(df)
        self.analyze_by_date(df)
        self.analyze_similarity_distribution(df)
        self.find_high_confidence_predictions(df, min_confidence=75.0)
        
        # Rapport du jour
        today = date.today().strftime('%Y-%m-%d')
        self.generate_daily_report(today)
        
        logger.info("\n✅ === ANALYSE TERMINÉE ===")

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Analyseur de prédictions de football")
    parser.add_argument('--date', type=str, help="Date pour rapport quotidien (YYYY-MM-DD)")
    parser.add_argument('--export', action='store_true', help="Exporter données filtrées")
    parser.add_argument('--league', nargs='+', help="Filtrer par ligues")
    
    args = parser.parse_args()
    
    analyzer = PredictionsAnalyzer()
    
    if args.date:
        # Rapport pour une date spécifique
        analyzer.generate_daily_report(args.date)
    elif args.export:
        # Export filtré
        df = analyzer.load_historical_data()
        filters = {}
        if args.league:
            filters['league'] = args.league
        analyzer.export_filtered_data(df, filters)
    else:
        # Analyse complète
        analyzer.run_complete_analysis()

if __name__ == "__main__":
    main()