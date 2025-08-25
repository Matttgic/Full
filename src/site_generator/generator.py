import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime

def generate_site():
    """
    Génère le site web statique des prédictions de football.
    """
    print("🚀 Démarrage de la génération du site...")

    # Configuration des chemins
    templates_dir = 'src/site_generator/templates'
    static_dir = 'src/site_generator/static'
    output_dir = 'docs'

    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'static'), exist_ok=True)

    # Initialiser Jinja2
    env = Environment(loader=FileSystemLoader(templates_dir))

    # --- Données pour la page d'accueil (Prédictions du jour) ---
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    predictions_path = f'data/predictions/daily_elo_predictions_{today_str}.csv'
    predictions_data = []
    if os.path.exists(predictions_path):
        try:
            df_preds = pd.read_csv(predictions_path)
            # Remplacer les NaN par une chaîne vide pour l'affichage
            df_preds.fillna('', inplace=True)
            predictions_data = df_preds.to_dict(orient='records')
            print(f"✅ {len(predictions_data)} prédictions du jour chargées.")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des prédictions du jour: {e}")
    else:
        print(f"ℹ️ Aucun fichier de prédictions trouvé pour aujourd'hui: {predictions_path}")

    # --- Données pour la page de bilan ---
    summary_path = 'data/analysis/elo_summary.csv'
    summary_data = []
    if os.path.exists(summary_path):
        try:
            df_summary = pd.read_csv(summary_path)
            summary_data = df_summary.to_dict(orient='records')
            print(f"✅ Bilan statistique chargé: {len(summary_data)} lignes.")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement du bilan: {e}")
    else:
        print(f"ℹ️ Aucun fichier de bilan trouvé: {summary_path}")

    # Paramètres communs pour les modèles
    template_params = {
        "generation_date": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }

    # Générer index.html
    template_index = env.get_template('index.html')
    index_params = {**template_params, "predictions": predictions_data, "date": today_str}
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(template_index.render(index_params))
    print("✅ Page 'index.html' générée.")

    # Générer summary.html
    template_summary = env.get_template('summary.html')
    summary_params = {**template_params, "summary": summary_data}
    with open(os.path.join(output_dir, 'summary.html'), 'w', encoding='utf-8') as f:
        f.write(template_summary.render(summary_params))
    print("✅ Page 'summary.html' générée.")

    # Copier les fichiers statiques (CSS)
    static_files = os.listdir(static_dir)
    for file_name in static_files:
        full_file_name = os.path.join(static_dir, file_name)
        if os.path.isfile(full_file_name):
            # Utiliser shutil pour une copie plus robuste
            import shutil
            shutil.copy(full_file_name, os.path.join(output_dir, 'static', file_name))
    print(f"✅ {len(static_files)} fichier(s) statique(s) copié(s).")

    print("🎉 Site généré avec succès !")

if __name__ == "__main__":
    generate_site()
