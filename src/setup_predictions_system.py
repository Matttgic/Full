#!/usr/bin/env python3
"""
Script de configuration et setup du système de prédictions
"""

import os
import logging
import subprocess
import sys
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    logger.info("🔍 Vérification des dépendances...")
    
    required_packages = [
        'pandas', 'numpy', 'requests', 'schedule'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"❌ {package} - MANQUANT")
    
    if missing_packages:
        logger.info(f"📦 Installation des packages manquants: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            logger.info("✅ Installation terminée")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Erreur d'installation: {e}")
            return False
    
    return True

def setup_directories():
    """Crée la structure de dossiers nécessaire"""
    logger.info("📁 Création de la structure de dossiers...")
    
    directories = [
        'data/predictions',
        'data/predictions/archives',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ {directory}")

def check_api_key():
    """Vérifie la présence de la clé API"""
    logger.info("🔑 Vérification de la clé API...")
    
    api_key = os.environ.get('RAPIDAPI_KEY')
    if not api_key:
        logger.error("❌ RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        logger.info("💡 Ajoutez votre clé: export RAPIDAPI_KEY='your_key_here'")
        return False
    
    logger.info("✅ RAPIDAPI_KEY trouvée")
    return True

def check_historical_data():
    """Vérifie la présence des données historiques"""
    logger.info("📊 Vérification des données historiques...")
    
    odds_dir = 'data/odds/raw_data'
    if not os.path.exists(odds_dir):
        logger.warning(f"❌ Dossier des cotes non trouvé: {odds_dir}")
        return False
    
    # Compter les fichiers de cotes
    odds_files = [f for f in os.listdir(odds_dir) if f.endswith('_complete_odds.csv')]
    logger.info(f"📈 {len(odds_files)} fichiers de cotes trouvés")
    
    if len(odds_files) < 5:
        logger.warning("⚠️ Peu de données historiques disponibles (< 5 ligues)")
        logger.info("💡 Lancez d'abord les collecteurs de données pour avoir plus de données")
    
    return len(odds_files) > 0

def test_prediction_workflow():
    """Test rapide du workflow de prédictions"""
    logger.info("🧪 Test du workflow de prédictions...")
    
    try:
        # Import test
        from daily_predictions_workflow import DailyPredictionsWorkflow
        logger.info("✅ Import du workflow réussi")
        
        # Test avec clé API (sans exécution complète)
        api_key = os.environ.get('RAPIDAPI_KEY')
        if api_key:
            workflow = DailyPredictionsWorkflow(api_key)
            logger.info("✅ Initialisation du workflow réussie")
            
            # Test de chargement des données historiques
            if len(workflow.historical_odds_data) > 0:
                logger.info(f"✅ Données historiques chargées: {len(workflow.historical_odds_data)} entrées")
            else:
                logger.warning("⚠️ Aucune donnée historique chargée")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur test workflow: {e}")
        return False

def create_systemd_service():
    """Crée un fichier de service systemd (optionnel)"""
    logger.info("⚙️ Création du fichier de service systemd...")
    
    service_content = f"""[Unit]
Description=Football Predictions Scheduler
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={os.getcwd()}
Environment=RAPIDAPI_KEY={os.environ.get('RAPIDAPI_KEY', 'YOUR_API_KEY')}
ExecStart=/usr/bin/python3 {os.getcwd()}/scheduler_predictions.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
    
    service_file = '/tmp/football-predictions.service'
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        logger.info(f"✅ Fichier de service créé: {service_file}")
        logger.info("💡 Pour l'installer:")
        logger.info(f"   sudo cp {service_file} /etc/systemd/system/")
        logger.info("   sudo systemctl daemon-reload")
        logger.info("   sudo systemctl enable football-predictions")
        logger.info("   sudo systemctl start football-predictions")
        
    except Exception as e:
        logger.warning(f"⚠️ Erreur création service: {e}")

def show_usage_examples():
    """Affiche des exemples d'utilisation"""
    logger.info("\n📚 === EXEMPLES D'UTILISATION ===")
    
    examples = [
        ("Lancer le workflow une fois:", "python3 daily_predictions_workflow.py"),
        ("Démarrer le scheduler:", "python3 scheduler_predictions.py"),
        ("Analyser les résultats:", "python3 predictions_analyzer.py"),
        ("Rapport pour une date:", "python3 predictions_analyzer.py --date 2025-01-15"),
        ("Exporter données filtrées:", "python3 predictions_analyzer.py --export --league 'Premier League' 'La Liga'"),
    ]
    
    for description, command in examples:
        print(f"  • {description}")
        print(f"    {command}")
        print()

def main():
    """Setup complet du système"""
    logger.info("🚀 === SETUP SYSTÈME DE PRÉDICTIONS FOOTBALL ===")
    
    # Vérifications
    checks = [
        ("Dépendances", check_dependencies),
        ("Dossiers", lambda: (setup_directories(), True)[1]),
        ("Clé API", check_api_key),
        ("Données historiques", check_historical_data),
        ("Workflow", test_prediction_workflow),
    ]
    
    all_ok = True
    for name, check_func in checks:
        logger.info(f"\n--- {name} ---")
        if not check_func():
            all_ok = False
    
    # Service systemd (optionnel)
    logger.info("\n--- Service Systemd ---")
    create_systemd_service()
    
    # Résumé
    logger.info("\n🎉 === SETUP TERMINÉ ===")
    if all_ok:
        logger.info("✅ Tous les tests sont passés !")
        logger.info("🚀 Le système est prêt à être utilisé")
    else:
        logger.warning("⚠️ Certains tests ont échoué")
        logger.info("💡 Corrigez les problèmes avant de lancer le système")
    
    # Exemples d'utilisation
    show_usage_examples()
    
    # Proposition de lancement
    if all_ok:
        logger.info("🎯 PROCHAINES ÉTAPES:")
        logger.info("1. Lancez le workflow une fois pour tester:")
        logger.info("   python3 daily_predictions_workflow.py")
        logger.info("2. Ou démarrez le scheduler pour automatiser:")
        logger.info("   python3 scheduler_predictions.py")

if __name__ == "__main__":
    main()