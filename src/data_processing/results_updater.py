"""
Ce script est responsable de la mise à jour des prédictions historiques avec
leurs résultats de match réels.

Rôle :
- Charge l'historique complet des prédictions Elo.
- Charge les données de tous les matchs joués.
- Fusionne ces deux ensembles de données en se basant sur l'ID du match (fixture_id).
- Filtre pour ne garder que les matchs qui ont à la fois une prédiction et un résultat.
- Sauvegarde ce jeu de données complet dans `historical_elo_predictions_with_results.csv`.

Ce script est une brique essentielle de la pipeline, car il crée les données
nécessaires au script `elo_summary.py` pour analyser la performance du modèle.
"""
import pandas as pd
import numpy as np
import os
import glob
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_predictions_with_results():
    """
    Met à jour les prédictions Elo historiques avec les résultats des matchs.
    """
    logger.info("🚀 Démarrage de la mise à jour des prédictions avec les résultats...")

    # Définition des chemins
    predictions_path = 'data/predictions/historical_elo_predictions.csv'
    matches_dir = 'data/matches'
    output_path = 'data/predictions/historical_elo_predictions_with_results.csv'

    # --- Chargement des données ---

    # Charger les prédictions historiques
    if not os.path.exists(predictions_path):
        logger.error(f"Fichier des prédictions historiques non trouvé: {predictions_path}")
        return
    try:
        predictions_df = pd.read_csv(predictions_path)
        logger.info(f"✅ {len(predictions_df)} prédictions historiques chargées.")
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {predictions_path}: {e}")
        return

    # Charger tous les résultats de matchs
    match_files = glob.glob(os.path.join(matches_dir, '*.csv'))
    if not match_files:
        logger.error(f"Aucun fichier de match trouvé dans: {matches_dir}")
        return
    try:
        matches_df = pd.concat((pd.read_csv(f) for f in match_files), ignore_index=True)
        logger.info(f"✅ {len(matches_df)} résultats de matchs chargés depuis {len(match_files)} fichiers.")
    except Exception as e:
        logger.error(f"Erreur lors de la concaténation des fichiers de matchs: {e}")
        return

    # --- Fusion et traitement ---

    # Sélectionner les colonnes pertinentes des résultats
    results_cols = ['fixture_id', 'home_goals_fulltime', 'away_goals_fulltime']
    if not all(col in matches_df.columns for col in results_cols):
        # Fallback si les colonnes 'fulltime' n'existent pas
        results_cols = ['fixture_id', 'home_goals', 'away_goals']
        if not all(col in matches_df.columns for col in results_cols):
            logger.error("Les colonnes de score ('home_goals', 'away_goals') sont introuvables.")
            return
        matches_df.rename(columns={'home_goals': 'home_goals_fulltime', 'away_goals': 'away_goals_fulltime'}, inplace=True)

    results_df = matches_df[results_cols]

    # Fusionner les prédictions avec les résultats
    merged_df = pd.merge(predictions_df, results_df, on='fixture_id', how='left')

    # Filtrer pour ne garder que les matchs avec des résultats
    final_df = merged_df.dropna(subset=['home_goals_fulltime', 'away_goals_fulltime'])
    logger.info(f"📊 {len(final_df)} matchs avec prédictions et résultats trouvés.")

    if final_df.empty:
        logger.warning("Aucun match correspondant avec des résultats complets n'a été trouvé. Le fichier de sortie ne sera pas mis à jour.")
        # On crée quand même un fichier vide avec les bonnes colonnes pour la suite du workflow
        final_df = pd.DataFrame(columns=merged_df.columns)
    else:
        # Assurer que les types de données sont corrects
        final_df['home_goals_fulltime'] = final_df['home_goals_fulltime'].astype(int)
        final_df['away_goals_fulltime'] = final_df['away_goals_fulltime'].astype(int)

    # --- Sauvegarde ---
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_df.to_csv(output_path, index=False)
        logger.info(f"💾 Fichier de résultats combinés sauvegardé dans: {output_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier final: {e}")

    logger.info("✅ Mise à jour terminée.")

def main():
    """Point d'entrée principal du script."""
    update_predictions_with_results()

if __name__ == "__main__":
    main()
