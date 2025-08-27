# ⚽ Système de Prédiction de Football Basé sur l'ELO et les Cotes

##  Aperçu

Ce projet est un système complet pour collecter des données de football, calculer des classements ELO, et générer des prédictions de matchs basées sur la similarité des cotes historiques. Il est conçu pour être entièrement automatisé grâce à des workflows GitHub Actions.

## ✨ Fonctionnalités Clés

- **Collecte de Données Automatisée :** Récupère les informations sur les ligues, les matchs, les classements, et les cotes de plus de 15 ligues.
- **Calculateur ELO :** Intègre un système de classement ELO pour évaluer la force relative des équipes.
- **Moteur de Prédiction par Similarité :** Prédit les résultats des matchs en trouvant des rencontres historiques avec des profils de cotes similaires.
- **Génération Quotidienne Automatique :** Un workflow tourne chaque nuit pour générer les prédictions du jour.
- **Analyse et Rapports :** Inclut des outils pour analyser la performance des prédictions et les enrichir avec les résultats réels.
- **Filtrage des Paris :** L'analyse se concentre sur les types de paris les plus populaires : **1X2 (Match Winner)**, **Both Teams Score (BTTS)**, et **Goals Over/Under**.

## ⚙️ Comment ça Marche

Le système fonctionne en trois étapes principales :

1.  **Collecte de Données :** Des scripts automatisés (`GitHub Actions`) collectent en continu les données sur les matchs passés, futurs, et les cotes associées. Ces données sont stockées dans le dossier `data/`.
2.  **Génération de Prédictions :** Un autre script automatisé (`elo_prediction.yml`) s'exécute chaque nuit. Il utilise les données collectées pour calculer les probabilités de victoire (basées sur ELO) et les pourcentages de confiance (basés sur la similarité des cotes).
3.  **Analyse :** Des scripts dans `src/analysis` permettent d'analyser les prédictions, de les enrichir avec les résultats réels, et de tester la performance du système.

## 📂 Structure du Projet

Voici une description des fichiers et dossiers importants du projet :

```
.
├── .github/
│   └── workflows/        # Contient tous les scripts d'automatisation (GitHub Actions)
│       ├── elo_prediction.yml  # WORKFLOW PRINCIPAL : Génère les prédictions chaque nuit
│       └── ...             # Autres workflows pour la collecte de données
├── data/
│   ├── matches/            # Contient les résultats détaillés des matchs par ligue
│   ├── odds/
│   │   └── raw_data/       # Contient les données brutes des cotes pour tous les types de paris
│   └── predictions/        # Contient les fichiers de prédictions générés
│       ├── daily_elo_predictions_YYYY-MM-DD.csv   # Prédictions quotidiennes
│       └── historical_elo_predictions_with_results.csv # Fichier enrichi avec les résultats
├── src/                    # Contient tout le code source du projet
│   ├── analysis/           # Scripts pour l'analyse des données et des prédictions
│   │   └── predictions_analyzer.py # Contient la logique pour enrichir les données
│   ├── prediction/         # Scripts liés à la génération des prédictions
│   │   └── elo_prediction_workflow.py # Logique du workflow de prédiction ELO
│   ├── demo_predictions.py # Script pour lancer une démo du système sans appeler les APIs
│   └── test_complete_system.py # Script de test pour valider l'ensemble du système
├── README.md               # Ce fichier - une vue d'ensemble du projet
└── requirements.txt        # Liste des dépendances Python nécessaires
```

## 🚀 Comment Utiliser

- **Pour tester le système :** Le moyen le plus simple de vérifier que tout fonctionne est de lancer le script de test complet.
  ```bash
  python3 src/test_complete_system.py
  ```
- **Pour lancer une démo :** Pour voir le système générer des prédictions basées sur les données existantes (sans utiliser d'appels API), vous pouvez exécuter :
  ```bash
  python3 src/demo_predictions.py
  ```
- **Les prédictions réelles** sont générées automatiquement par le workflow `.github/workflows/elo_prediction.yml`. Les résultats apparaissent dans le dossier `data/predictions`.


## 📄 Licence

Ce projet est distribué sous la licence MIT. Consultez le fichier [LICENSE](LICENSE) pour plus d'informations.

