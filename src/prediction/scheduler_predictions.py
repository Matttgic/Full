#!/usr/bin/env python3
"""
Scheduler pour le workflow quotidien de prédictions
Lance les prédictions à des heures définies
"""

import schedule
import time
import logging
import subprocess
import os
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler_predictions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_daily_predictions():
    """Lance le workflow quotidien de prédictions"""
    logger.info("🔄 Lancement du workflow quotidien de prédictions...")
    
    try:
        # Exécuter le script de prédictions
        result = subprocess.run(
            ["python3", "/app/daily_predictions_workflow.py"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        
        if result.returncode == 0:
            logger.info("✅ Workflow de prédictions terminé avec succès")
            logger.info(f"Output: {result.stdout[-500:]}")  # Dernières 500 chars
        else:
            logger.error(f"❌ Erreur dans le workflow: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ Exception lors du lancement: {e}")

def run_results_updater():
    """Met à jour les prédictions avec les résultats réels"""
    logger.info("🔄 Lancement de la mise à jour des résultats...")

    try:
        result = subprocess.run(
            ["python3", "/app/results_updater.py"],
            capture_output=True,
            text=True,
            cwd="/app"
        )

        if result.returncode == 0:
            logger.info("✅ Mise à jour des résultats terminée")
        else:
            logger.warning(f"⚠️ Avertissement mise à jour résultats: {result.stderr[:200]}")

    except Exception as e:
        logger.error(f"❌ Exception lors de la mise à jour des résultats: {e}")

def run_data_collection():
    """Lance la collecte de données (optionnel - sync avec les autres workflows)"""
    logger.info("🔄 Lancement de la collecte de données...")
    
    try:
        # Lancer la mise à jour des données de matchs
        result1 = subprocess.run(
            ["python3", "/app/football_data_updater.py"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        
        if result1.returncode == 0:
            logger.info("✅ Mise à jour des données de matchs terminée")
        else:
            logger.warning(f"⚠️ Avertissement mise à jour matchs: {result1.stderr[:200]}")
        
        # Petite pause
        time.sleep(30)
        
        # Lancer la collecte des cotes
        result2 = subprocess.run(
            ["python3", "/app/football_odds_collector.py"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        
        if result2.returncode == 0:
            logger.info("✅ Collecte des cotes terminée")
        else:
            logger.warning(f"⚠️ Avertissement collecte cotes: {result2.stderr[:200]}")

        # Mettre à jour les résultats des matchs
        run_results_updater()

    except Exception as e:
        logger.error(f"❌ Exception lors de la collecte: {e}")

def main():
    """Configuration du scheduler"""
    logger.info("🚀 === DÉMARRAGE DU SCHEDULER DE PRÉDICTIONS ===")
    
    # Vérifier que la clé API est disponible
    if not os.environ.get('RAPIDAPI_KEY'):
        logger.error("⚠️ RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        return
    
    # Programmer les tâches
    
    # Collecte de données et prédictions le matin (06:00)
    schedule.every().day.at("06:00").do(run_data_collection)
    schedule.every().day.at("06:30").do(run_daily_predictions)
    
    # Mise à jour des prédictions en milieu de journée (12:00)
    schedule.every().day.at("12:00").do(run_daily_predictions)
    
    # Mise à jour des prédictions en soirée (18:00)
    schedule.every().day.at("18:00").do(run_data_collection)
    schedule.every().day.at("18:30").do(run_daily_predictions)
    
    # Prédictions finales de la journée (21:00)
    schedule.every().day.at("21:00").do(run_daily_predictions)
    
    logger.info("📅 Scheduler configuré:")
    logger.info("   - 06:00: Collecte données + mise à jour résultats")
    logger.info("   - 06:30: Prédictions matinales")
    logger.info("   - 12:00: Prédictions midi")
    logger.info("   - 18:00: Collecte données + mise à jour résultats")
    logger.info("   - 18:30: Prédictions soirée")
    logger.info("   - 21:00: Prédictions finales")
    
    # Lancer une première fois immédiatement pour test
    logger.info("🔄 Lancement initial pour test...")
    run_daily_predictions()
    
    # Boucle principale
    logger.info("⏰ Scheduler en cours d'exécution...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Vérifier toutes les minutes
            
            # Log de statut toutes les heures
            current_time = datetime.now()
            if current_time.minute == 0:
                logger.info(f"⏰ Scheduler actif - {current_time.strftime('%H:%M')} - Prochaine tâche: {schedule.next_run()}")
                
        except KeyboardInterrupt:
            logger.info("⏹️ Arrêt du scheduler demandé")
            break
        except Exception as e:
            logger.error(f"❌ Erreur dans le scheduler: {e}")
            time.sleep(300)  # Attendre 5 minutes avant de reprendre

if __name__ == "__main__":
    main()
