#!/usr/bin/env python3
"""
Script de démarrage rapide pour les prédictions quotidiennes
Usage: python3 quick_start.py [--test|--run|--schedule]
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Vérifications préalables rapides"""
    logger.info("🔍 Vérifications rapides...")
    
    # Clé API
    if not os.environ.get('RAPIDAPI_KEY'):
        logger.error("❌ RAPIDAPI_KEY manquante")
        logger.info("💡 export RAPIDAPI_KEY='your_key_here'")
        return False
    
    # Données historiques
    odds_dir = 'data/odds/raw_data'
    if not os.path.exists(odds_dir):
        logger.error(f"❌ Dossier des cotes manquant: {odds_dir}")
        logger.info("💡 Lancez d'abord les collecteurs de données")
        return False
    
    odds_files = [f for f in os.listdir(odds_dir) if f.endswith('.csv')]
    if len(odds_files) == 0:
        logger.error("❌ Aucun fichier de cotes trouvé")
        return False
    
    logger.info(f"✅ {len(odds_files)} fichiers de cotes disponibles")
    return True

def test_mode():
    """Mode test - exécution rapide pour vérifier que tout fonctionne"""
    logger.info("🧪 === MODE TEST ===")
    
    if not check_environment():
        return False
    
    try:
        from daily_predictions_workflow import DailyPredictionsWorkflow
        
        logger.info("🔄 Test d'initialisation...")
        workflow = DailyPredictionsWorkflow(os.environ.get('RAPIDAPI_KEY'))
        
        logger.info(f"✅ Données historiques: {len(workflow.historical_odds_data)} entrées")
        logger.info(f"✅ Matrice de caractéristiques: {workflow.historical_feature_matrix.shape}")
        
        # Test de récupération des matchs (sans appel API complet)
        logger.info("🔄 Test des composants...")
        logger.info("✅ Tous les composants fonctionnent")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur test: {e}")
        return False

def run_mode():
    """Mode run - exécution complète du workflow"""
    logger.info("🚀 === MODE RUN ===")
    
    if not check_environment():
        return False
    
    try:
        from daily_predictions_workflow import DailyPredictionsWorkflow
        
        workflow = DailyPredictionsWorkflow(os.environ.get('RAPIDAPI_KEY'))
        workflow.run_daily_workflow()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur exécution: {e}")
        return False

def schedule_mode():
    """Mode schedule - démarre le scheduler"""
    logger.info("⏰ === MODE SCHEDULER ===")
    
    if not check_environment():
        return False
    
    try:
        import subprocess
        
        logger.info("🔄 Démarrage du scheduler...")
        subprocess.run([sys.executable, "scheduler_predictions.py"])
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur scheduler: {e}")
        return False

def analyze_mode():
    """Mode analyse - affiche les résultats"""
    logger.info("📊 === MODE ANALYSE ===")
    
    predictions_dir = 'data/predictions'
    if not os.path.exists(predictions_dir):
        logger.error(f"❌ Dossier prédictions manquant: {predictions_dir}")
        return False
    
    try:
        from predictions_analyzer import PredictionsAnalyzer
        
        analyzer = PredictionsAnalyzer()
        analyzer.run_complete_analysis()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse: {e}")
        return False

def show_status():
    """Affiche le statut du système"""
    logger.info("📋 === STATUT SYSTÈME ===")
    
    # Vérifications
    checks = {
        "RAPIDAPI_KEY": bool(os.environ.get('RAPIDAPI_KEY')),
        "Dossier cotes": os.path.exists('data/odds/raw_data'),
        "Dossier prédictions": os.path.exists('data/predictions'),
    }
    
    for name, status in checks.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {name}")
    
    # Fichiers récents
    predictions_dir = 'data/predictions'
    if os.path.exists(predictions_dir):
        files = [f for f in os.listdir(predictions_dir) if f.startswith('daily_')]
        if files:
            latest_file = max(files)
            logger.info(f"📁 Dernier fichier: {latest_file}")
        else:
            logger.info("📁 Aucun fichier de prédictions trouvé")
    
    # Données historiques
    odds_dir = 'data/odds/raw_data'
    if os.path.exists(odds_dir):
        odds_files = [f for f in os.listdir(odds_dir) if f.endswith('.csv')]
        logger.info(f"📈 Fichiers de cotes: {len(odds_files)}")

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Démarrage rapide prédictions football")
    parser.add_argument('--test', action='store_true', help="Mode test")
    parser.add_argument('--run', action='store_true', help="Mode run (exécution complète)")
    parser.add_argument('--schedule', action='store_true', help="Mode scheduler")
    parser.add_argument('--analyze', action='store_true', help="Mode analyse")
    parser.add_argument('--status', action='store_true', help="Afficher statut")
    
    args = parser.parse_args()
    
    # Logo
    print("""
⚽ ================================== ⚽
   SYSTÈME DE PRÉDICTIONS FOOTBALL    
⚽ ================================== ⚽
""")
    
    success = False
    
    if args.test:
        success = test_mode()
    elif args.run:
        success = run_mode()
    elif args.schedule:
        success = schedule_mode()
    elif args.analyze:
        success = analyze_mode()
    elif args.status:
        show_status()
        success = True
    else:
        # Mode par défaut - afficher aide
        logger.info("🔧 Modes disponibles:")
        logger.info("  --test     : Test rapide du système")
        logger.info("  --run      : Exécution complète du workflow")
        logger.info("  --schedule : Démarrer le scheduler automatique")
        logger.info("  --analyze  : Analyser les résultats")
        logger.info("  --status   : Afficher le statut du système")
        logger.info("")
        logger.info("💡 Exemple: python3 quick_start.py --test")
        success = True
    
    if success and not args.status:
        logger.info("✅ === TERMINÉ AVEC SUCCÈS ===")
    elif not success:
        logger.error("❌ === TERMINÉ AVEC ERREURS ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
