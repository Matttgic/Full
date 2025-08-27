#!/usr/bin/env python3
"""
Configuration de la clé RAPIDAPI pour le système de prédictions
"""

import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def configure_api_key():
    """Configure la clé RAPIDAPI dans l'environnement"""
    
    # Votre clé RAPIDAPI
    RAPIDAPI_KEY = 'e1e76b8e3emsh2445ffb97db0128p158afdjsnb3175ce8d916'
    
    # Définir dans l'environnement
    os.environ['RAPIDAPI_KEY'] = RAPIDAPI_KEY
    
    logger.info("✅ RAPIDAPI_KEY configurée dans l'environnement")
    
    # Test de la clé
    try:
        from daily_predictions_workflow import DailyPredictionsWorkflow
        
        workflow = DailyPredictionsWorkflow(RAPIDAPI_KEY)
        logger.info(f"✅ Connexion API testée avec succès")
        logger.info(f"📊 Données historiques disponibles: {len(workflow.historical_odds_data):,}")
        logger.info(f"🎯 Matrice de référence: {workflow.historical_feature_matrix.shape[0]} matchs")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur test API: {e}")
        return False

def create_env_file():
    """Crée un fichier .env avec la clé API"""
    
    env_content = """# Configuration du système de prédictions football
RAPIDAPI_KEY=e1e76b8e3emsh2445ffb97db0128p158afdjsnb3175ce8d916

# Instructions d'utilisation:
# Source ce fichier avant de lancer les scripts:
# source .env
# puis: python3 daily_predictions_workflow.py
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        
        logger.info("✅ Fichier .env créé avec votre clé API")
        logger.info("💡 Usage: source .env avant de lancer les scripts")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur création .env: {e}")
        return False

def main():
    """Configuration complète"""
    logger.info("🔑 === CONFIGURATION CLEF API ===")
    
    # Configurer dans l'environnement actuel
    if configure_api_key():
        logger.info("✅ Configuration réussie")
    else:
        logger.error("❌ Configuration échouée")
        return
    
    # Créer fichier .env pour utilisation future
    create_env_file()
    
    logger.info("\n🚀 === SYSTÈME PRÊT ===")
    logger.info("Vous pouvez maintenant utiliser:")
    logger.info("• python3 daily_predictions_workflow.py")
    logger.info("• python3 scheduler_predictions.py")
    logger.info("• python3 quick_start.py --run")
    
    logger.info("\n📋 Ou pour les sessions futures:")
    logger.info("• source .env")
    logger.info("• python3 daily_predictions_workflow.py")

if __name__ == "__main__":
    main()
