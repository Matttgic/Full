import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime

def load_csv_to_dict(path, file_type=""):
    """Charge un fichier CSV et le retourne comme une liste de dictionnaires."""
    if not os.path.exists(path):
        print(f"ℹ️ Fichier non trouvé pour {file_type}: {path}")
        return []
    try:
        df = pd.read_csv(path)
        # Remplacer les NaN par None pour une meilleure gestion par Jinja2
        df = df.replace({np.nan: None})
        print(f"✅ {len(df)} lignes chargées depuis {path}")
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement de {path}: {e}")
        return []

def generate_site():
    """
    Génère le site web statique complet avec toutes les prédictions et historiques.
    """
    print("🚀 Démarrage de la génération du site web complet...")

    # Configuration des chemins
    templates_dir = 'src/site_generator/templates'
    static_dir = 'src/site_generator/static'
    output_dir = 'docs'

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'static'), exist_ok=True)

    # Initialiser Jinja2
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

    # --- Chargement de toutes les données ---
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    # Prédictions du jour
    elo_preds_path = f'data/predictions/daily_elo_predictions_{today_str}.csv'
    odds_preds_path = f'data/predictions/daily_{today_str}.csv'
    elo_predictions_data = load_csv_to_dict(elo_preds_path, "Prédictions Elo du jour")
    odds_predictions_data = load_csv_to_dict(odds_preds_path, "Prédictions Cotes du jour")

    # Bilan et Historiques
    summary_path = 'data/analysis/elo_summary.csv'
    elo_history_path = 'data/predictions/historical_elo_predictions.csv'
    odds_history_path = 'data/predictions/historical_predictions.csv'
    summary_data = load_csv_to_dict(summary_path, "Bilan Elo")
    elo_history_data = load_csv_to_dict(elo_history_path, "Historique Elo")
    odds_history_data = load_csv_to_dict(odds_history_path, "Historique Cotes")

    # Paramètres communs pour les modèles
    template_params = {
        "generation_date": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "today_date": today_str
    }

    # --- Génération des pages ---
    pages_to_render = {
        "index.html": {"predictions": elo_predictions_data, "date": today_str},
        "odds_predictions.html": {"predictions": odds_predictions_data, "date": today_str},
        "elo_summary.html": {"summary": summary_data},
        "elo_history.html": {"history": elo_history_data},
        "odds_history.html": {"history": odds_history_data}
    }

    for template_name, data in pages_to_render.items():
        template = env.get_template(template_name)
        params = {**template_params, **data}
        with open(os.path.join(output_dir, template_name), 'w', encoding='utf-8') as f:
            f.write(template.render(params))
        print(f"✅ Page '{template_name}' générée.")

    # Copier les fichiers statiques (CSS)
    import shutil
    static_output_dir = os.path.join(output_dir, 'static')
    static_files = os.listdir(static_dir)
    for file_name in static_files:
        full_file_name = os.path.join(static_dir, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, static_output_dir)
    print(f"✅ {len(static_files)} fichier(s) statique(s) copié(s).")

    print("🎉 Site généré avec succès !")

if __name__ == "__main__":
    generate_site()
