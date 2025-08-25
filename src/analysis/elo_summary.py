"""
Ce script fournit un bilan statistique de la performance du modèle Elo.

Rôle :
- Charge les prédictions Elo historiques et les résultats réels des matchs.
- Fusionne ces deux sources de données.
- Regroupe les matchs par tranches de différence d'Elo (par exemple, de 0 à 99,
  de 100 à 199, etc.).
- Pour chaque tranche, calcule des statistiques clés :
    - Le pourcentage de victoires à domicile, de nuls et de victoires à l'extérieur.
    - La moyenne de buts par match.
    - Le pourcentage de matchs où les deux équipes ont marqué (BTTS).
- Affiche un tableau de synthèse clair dans la console.

Ce script est un outil puissant pour évaluer la pertinence du modèle Elo et
identifier des tendances statistiques.

Pour l'exécuter :
python3 src/analysis/elo_summary.py
"""
import pandas as pd
import numpy as np
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_elo_predictions():
    """
    Analyse les prédictions Elo historiques pour en tirer des statistiques.
    """
    logger.info("📊 Démarrage de l'analyse des prédictions Elo...")

    # --- Chargement et fusion des données ---
    predictions_path = 'data/predictions/historical_elo_predictions.csv'
    matches_dir = 'data/matches'

    if not os.path.exists(predictions_path):
        logger.error(f"Le fichier de prédictions n'a pas été trouvé: {predictions_path}")
        return

    # Charger les prédictions
    try:
        predictions_df = pd.read_csv(predictions_path)
        logger.info(f"Données de prédictions chargées: {len(predictions_df)} lignes.")
    except Exception as e:
        logger.error(f"Erreur lors du chargement des prédictions: {e}")
        return

    # Charger tous les résultats de matchs
    all_matches_files = [os.path.join(matches_dir, f) for f in os.listdir(matches_dir) if f.endswith('.csv')]
    if not all_matches_files:
        logger.error("Aucun fichier de match trouvé dans le dossier 'data/matches'.")
        return

    matches_list = [pd.read_csv(file) for file in all_matches_files]
    matches_df = pd.concat(matches_list, ignore_index=True)
    logger.info(f"Données de matchs chargées: {len(matches_df)} matchs au total.")

    # Garder les colonnes nécessaires et renommer pour la cohérence
    matches_df = matches_df[['fixture_id', 'home_goals', 'away_goals']]
    matches_df.rename(columns={'home_goals': 'home_goals_fulltime', 'away_goals': 'away_goals_fulltime'}, inplace=True)

    # Fusionner les prédictions avec les résultats
    df = pd.merge(predictions_df, matches_df, on='fixture_id', how='inner')
    logger.info(f"Données fusionnées: {len(df)} matchs avec prédictions et résultats.")

    # --- Préparation des données ---
    df.dropna(subset=['home_goals_fulltime', 'away_goals_fulltime'], inplace=True)
    logger.info(f"Matchs avec résultats valides après fusion: {len(df)}")

    if df.empty:
        logger.warning("Aucun match avec des résultats complets à analyser.")
        return

    # Conversion des types de données
    df['home_goals_fulltime'] = pd.to_numeric(df['home_goals_fulltime'])
    df['away_goals_fulltime'] = pd.to_numeric(df['away_goals_fulltime'])

    # Calculer la différence d'Elo si elle n'existe pas
    if 'elo_difference' not in df.columns:
        df['elo_difference'] = df['home_team_elo'] - df['away_team_elo']

    # Déterminer le résultat du match (Victoire Domicile, Nul, Victoire Extérieur)
    df['result'] = np.where(
        df['home_goals_fulltime'] > df['away_goals_fulltime'], 'H',
        np.where(df['home_goals_fulltime'] < df['away_goals_fulltime'], 'A', 'D')
    )

    # Déterminer si les deux équipes ont marqué (BTTS)
    df['btts'] = ((df['home_goals_fulltime'] > 0) & (df['away_goals_fulltime'] > 0)).astype(int)

    # Calculer le total des buts
    df['total_goals'] = df['home_goals_fulltime'] + df['away_goals_fulltime']

    logger.info("Données préparées pour l'analyse.")

    # --- Analyse par tranches de différence d'Elo ---
    # Définir les tranches (bins) pour la différence d'Elo
    elo_bins = list(range(-500, 501, 100))
    elo_labels = [f"{i} à {i+99}" for i in elo_bins[:-1]]

    df['elo_bin'] = pd.cut(df['elo_difference'], bins=elo_bins, labels=elo_labels, right=False)

    # Calculer les statistiques par tranche
    summary = df.groupby('elo_bin').agg(
        total_matches=('fixture_id', 'count'),
        home_wins=('result', lambda x: (x == 'H').sum()),
        draws=('result', lambda x: (x == 'D').sum()),
        away_wins=('result', lambda x: (x == 'A').sum()),
        avg_total_goals=('total_goals', 'mean'),
        btts_pct=('btts', 'mean')
    ).reset_index()

    # Calculer les pourcentages
    summary['home_win_pct'] = (summary['home_wins'] / summary['total_matches']) * 100
    summary['draw_pct'] = (summary['draws'] / summary['total_matches']) * 100
    summary['away_win_pct'] = (summary['away_wins'] / summary['total_matches']) * 100
    summary['btts_pct'] *= 100

    # Formater les résultats pour l'affichage
    summary_display = summary[[
        'elo_bin', 'total_matches', 'home_win_pct', 'draw_pct', 'away_win_pct',
        'avg_total_goals', 'btts_pct'
    ]].copy()

    summary_display.rename(columns={
        'elo_bin': 'Différence Elo (Domicile - Extérieur)',
        'total_matches': 'Nb Matchs',
        'home_win_pct': '% Victoire Domicile',
        'draw_pct': '% Nul',
        'away_win_pct': '% Victoire Extérieur',
        'avg_total_goals': 'Moy. Buts Total',
        'btts_pct': '% BTTS'
    }, inplace=True)

    # Affichage des résultats dans la console
    logger.info("📈 Bilan Statistique par Différence d'Elo 📈")
    print(summary_display.to_string(index=False, float_format="%.2f"))

    logger.info("✅ Analyse terminée.")

def main():
    """
    Point d'entrée principal pour le script d'analyse.
    """
    analyze_elo_predictions()

if __name__ == "__main__":
    main()
