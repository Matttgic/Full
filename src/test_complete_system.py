#!/usr/bin/env python3
"""
Test complet du système de prédictions de football
Démontre toutes les fonctionnalités du workflow
"""

import os
import sys
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_demo_workflow():
    """Test du workflow de démonstration"""
    logger.info("🎭 === TEST DU WORKFLOW DÉMONSTRATION ===")
    
    try:
        from demo_predictions import DemoPredictionsWorkflow
        
        workflow = DemoPredictionsWorkflow()
        workflow.run_demo_workflow()
        
        return True
    except Exception as e:
        logger.error(f"❌ Erreur workflow démo: {e}")
        return False

def test_analyzer():
    """Test de l'analyseur de prédictions"""
    logger.info("📊 === TEST DE L'ANALYSEUR ===")
    
    try:
        from analysis.predictions_analyzer import PredictionsAnalyzer
        import pandas as pd
        
        analyzer = PredictionsAnalyzer()
        analyzer.historical_file = 'data/predictions/demo_historical_predictions.csv'
        
        # Vérifier que le fichier existe
        if not os.path.exists(analyzer.historical_file):
            logger.error("❌ Fichier de démo non trouvé")
            return False
        
        # Charger et analyser
        df = analyzer.load_historical_data()
        if df.empty:
            logger.error("❌ Aucune donnée chargée")
            return False
        
        logger.info(f"✅ {len(df)} prédictions chargées")
        
        # Tests des fonctions d'analyse
        analyzer.analyze_by_league(df)
        analyzer.analyze_similarity_distribution(df)
        analyzer.find_high_confidence_predictions(df, min_confidence=75.0)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur analyseur: {e}")
        return False

def test_data_integrity():
    """Test de l'intégrité des données"""
    logger.info("🔍 === TEST INTÉGRITÉ DES DONNÉES ===")
    
    # Vérifier les données historiques
    odds_dir = 'data/odds/raw_data'
    if not os.path.exists(odds_dir):
        logger.error(f"❌ Dossier des cotes manquant: {odds_dir}")
        return False
    
    odds_files = [f for f in os.listdir(odds_dir) if f.endswith('.csv')]
    logger.info(f"✅ {len(odds_files)} fichiers de cotes trouvés")
    
    if len(odds_files) == 0:
        logger.error("❌ Aucun fichier de cotes")
        return False
    
    # Vérifier les prédictions générées
    predictions_dir = 'data/predictions'
    if os.path.exists(predictions_dir):
        pred_files = [f for f in os.listdir(predictions_dir) if f.endswith('.csv')]
        logger.info(f"✅ {len(pred_files)} fichiers de prédictions trouvés")
    
    return True

def test_csv_format():
    """Test du format des CSV générés"""
    logger.info("📋 === TEST FORMAT CSV ===")
    
    try:
        import pandas as pd
        
        demo_file = 'data/predictions/demo_daily_2025-08-22.csv'
        if os.path.exists(demo_file):
            df = pd.read_csv(demo_file)
            
            logger.info(f"✅ CSV chargé: {len(df)} lignes, {len(df.columns)} colonnes")
            
            # Vérifier les colonnes essentielles
            essential_cols = [
                'date', 'home_team', 'away_team', 'league_name', 
                'total_bet_types_analyzed'
            ]
            
            missing_cols = [col for col in essential_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"❌ Colonnes manquantes: {missing_cols}")
                return False
            
            logger.info("✅ Toutes les colonnes essentielles présentes")
            
            # Vérifier les colonnes de similarité
            similarity_cols = [col for col in df.columns if col.endswith('_similarity_pct')]
            confidence_cols = [col for col in df.columns if col.endswith('_confidence')]
            
            logger.info(f"✅ {len(similarity_cols)} colonnes de similarité")
            logger.info(f"✅ {len(confidence_cols)} colonnes de confiance")
            
            # Vérifier les valeurs de similarité
            for col in similarity_cols[:5]:  # Tester les 5 premières
                values = df[col].dropna()
                if len(values) > 0:
                    valid_values = values[(values >= 0) & (values <= 100)]
                    if len(valid_values) != len(values):
                        logger.warning(f"⚠️ Valeurs invalides dans {col}")
                    else:
                        logger.info(f"✅ {col}: valeurs valides (0-100%)")
            
            return True
        else:
            logger.error(f"❌ Fichier CSV de test non trouvé: {demo_file}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur test CSV: {e}")
        return False

def show_system_summary():
    """Affiche un résumé complet du système"""
    logger.info("📋 === RÉSUMÉ DU SYSTÈME ===")
    
    # Données historiques
    odds_dir = 'data/odds/raw_data'
    if os.path.exists(odds_dir):
        odds_files = [f for f in os.listdir(odds_dir) if f.endswith('.csv')]
        
        total_lines = 0
        for file in odds_files[:5]:  # Compter les 5 premiers
            try:
                import pandas as pd
                df = pd.read_csv(os.path.join(odds_dir, file))
                total_lines += len(df)
            except:
                pass
        
        logger.info(f"📊 Données historiques:")
        logger.info(f"   • {len(odds_files)} ligues couvertes")
        logger.info(f"   • ~{total_lines:,} cotes historiques (échantillon)")
    
    # Prédictions
    predictions_dir = 'data/predictions'
    if os.path.exists(predictions_dir):
        pred_files = [f for f in os.listdir(predictions_dir) if f.endswith('.csv')]
        logger.info(f"🎯 Prédictions générées:")
        logger.info(f"   • {len(pred_files)} fichiers de prédictions")
        
        # Détails du dernier fichier
        if pred_files:
            latest_file = max(pred_files)
            try:
                import pandas as pd
                df = pd.read_csv(os.path.join(predictions_dir, latest_file))
                similarity_cols = [col for col in df.columns if col.endswith('_similarity_pct')]
                logger.info(f"   • Dernier fichier: {latest_file}")
                logger.info(f"   • {len(df)} matchs analysés")
                logger.info(f"   • {len(similarity_cols)} types de paris")
            except:
                pass
    
    # Capacités du système
    logger.info("🚀 Capacités du système:")
    logger.info("   • Analyse de similarité basée sur 15 ligues")
    logger.info("   • Support de 1000+ types de paris différents")
    logger.info("   • Génération de CSV quotidiens et historiques")
    logger.info("   • Système de scoring de confiance")
    logger.info("   • Analyses statistiques avancées")
    logger.info("   • Scheduling automatique (prêt)")

def generate_sample_report():
    """Génère un rapport d'exemple avec les meilleures prédictions"""
    logger.info("📈 === RAPPORT D'EXEMPLE ===")
    
    try:
        import pandas as pd
        
        demo_file = 'data/predictions/demo_daily_2025-08-22.csv'
        if os.path.exists(demo_file):
            df = pd.read_csv(demo_file)
            
            # Trouver les meilleures prédictions
            similarity_cols = [col for col in df.columns if col.endswith('_similarity_pct')]
            confidence_cols = [col for col in df.columns if col.endswith('_confidence')]
            
            best_predictions = []
            
            for _, row in df.iterrows():
                match_name = f"{row['home_team']} vs {row['away_team']}"
                league = row['league_name']
                
                for col in confidence_cols:
                    if pd.notna(row[col]) and row[col] >= 80:
                        bet_type = col.replace('_confidence', '')
                        similarity_col = f"{bet_type}_similarity_pct"
                        odd_col = f"{bet_type}_target_odd"
                        
                        if similarity_col in df.columns and odd_col in df.columns:
                            best_predictions.append({
                                'match': match_name,
                                'league': league,
                                'bet_type': bet_type.replace('_', ' ')[:40],
                                'confidence': row[col],
                                'similarity': row.get(similarity_col, 'N/A'),
                                'odd': row.get(odd_col, 'N/A')
                            })
            
            # Trier par confiance
            best_predictions = sorted(best_predictions, key=lambda x: x['confidence'], reverse=True)
            
            logger.info("🔥 TOP PRÉDICTIONS (Confiance ≥ 80%):")
            for i, pred in enumerate(best_predictions[:10]):
                logger.info(f"{i+1:2d}. {pred['match'][:30]:30} | {pred['league'][:15]:15} | {pred['bet_type']:40} | Conf: {pred['confidence']:5.1f}% | Sim: {pred['similarity']:5.1f}% | Cote: {pred['odd']}")
            
            if not best_predictions:
                logger.info("   Aucune prédiction avec confiance ≥ 80% dans cet échantillon")
                logger.info("   (Réduisez le seuil ou attendez plus de données historiques)")
        
    except Exception as e:
        logger.error(f"❌ Erreur génération rapport: {e}")

def main():
    """Test complet du système"""
    print("""
⚽ ================================================ ⚽
   TEST COMPLET SYSTÈME PRÉDICTIONS FOOTBALL       
⚽ ================================================ ⚽
""")
    
    tests = [
        ("Intégrité des données", test_data_integrity),
        ("Workflow démonstration", test_demo_workflow),
        ("Format CSV", test_csv_format),
        ("Analyseur", test_analyzer),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            logger.info(f"✅ {test_name}: RÉUSSI")
        else:
            logger.error(f"❌ {test_name}: ÉCHOUÉ")
    
    # Résumé des tests
    logger.info(f"\n🏆 === RÉSULTATS DES TESTS ===")
    logger.info(f"✅ Tests réussis: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 TOUS LES TESTS SONT PASSÉS !")
        
        # Afficher le résumé du système
        show_system_summary()
        
        # Générer un rapport d'exemple
        generate_sample_report()
        
        logger.info("\n🚀 === SYSTÈME PRÊT À L'EMPLOI ===")
        logger.info("Le système de prédictions est opérationnel !")
        logger.info("Prochaines étapes:")
        logger.info("1. Configurez RAPIDAPI_KEY pour utilisation en production")
        logger.info("2. Lancez le scheduler: python3 scheduler_predictions.py")
        logger.info("3. Ou utilisez: python3 quick_start.py --run")
        
    else:
        logger.error("❌ Certains tests ont échoué")
        logger.info("💡 Vérifiez les erreurs ci-dessus et corrigez-les")

if __name__ == "__main__":
    main()