# 🏆 Système de Prédictions Football Quotidiennes

## 📖 Description

Ce système génère automatiquement des prédictions quotidiennes pour les matchs de football en utilisant l'analyse de similarité des cotes. Il combine les données historiques de 15 ligues européennes et saoudiennes pour produire des pourcentages de similarité robustes pour tous les types de paris.

## 🎯 Fonctionnalités

- **Prédictions quotidiennes** : Génère un CSV quotidien avec tous les matchs du jour
- **Analyse complète** : Calcule les % de similarité pour TOUS les types de paris
- **Base de données robuste** : Utilise les données combinées de 15 ligues
- **Historique complet** : Maintient un CSV historique pour analyses avancées
- **Scheduling automatique** : Exécution automatisée à heures définies
- **Analyses avancées** : Outils d'analyse et de visualisation des résultats

## 📁 Structure des Fichiers

```
/
├── src/
│   ├── data_processing/
│   │   ├── football_data_collector_extended.py
│   │   └── ...
│   ├── prediction/
│   │   ├── daily_predictions_workflow.py
│   │   └── ...
│   └── analysis/
│       ├── predictions_analyzer.py
│       ├── elo_calculator.py
│       └── ...
├── data/
│   ├── predictions/
│   │   ├── daily_YYYY-MM-DD.csv
│   │   └── historical_predictions.csv
│   ├── elo_ratings.csv
│   └── ...
├── .github/workflows/
│   ├── prediction_workflow.yml
│   └── ...
└── README_PREDICTIONS.md
```

## 🚀 Installation & Configuration

### 1. Installation des dépendances

```bash
pip install -r requirements.txt
```

### 2. Configuration de la clé API

```bash
export RAPIDAPI_KEY='your_rapidapi_key_here'
```

### 3. Setup automatique

```bash
python3 src/setup_predictions_system.py
```

## 🎮 Utilisation

### Démarrage Rapide

```bash
# Test du système
python3 src/quick_start.py --test

# Exécution unique
python3 src/quick_start.py --run

# Démarrer le scheduler
python3 src/quick_start.py --schedule

# Analyser les résultats
python3 src/quick_start.py --analyze

# Vérifier le statut
python3 src/quick_start.py --status
```

### Utilisation Détaillée

#### 1. Workflow Quotidien

```bash
# Exécution manuelle du workflow
python3 src/prediction/daily_predictions_workflow.py
```

#### 2. Scheduler Automatique

```bash
# Démarrer le scheduler (reste en cours d'exécution)
python3 src/prediction/scheduler_predictions.py
```

**Horaires configurés :**
- 06:00 : Collecte de données
- 06:30 : Prédictions matinales
- 12:00 : Prédictions midi
- 18:00 : Collecte de données
- 18:30 : Prédictions soirée
- 21:00 : Prédictions finales

#### 3. Analyse des Résultats

```bash
# Analyse complète
PYTHONPATH=src python3 src/analysis/predictions_analyzer.py

# Rapport pour une date spécifique
PYTHONPATH=src python3 src/analysis/predictions_analyzer.py --date 2025-01-15

# Export filtré par ligues
PYTHONPATH=src python3 src/analysis/predictions_analyzer.py --export --league "Premier League" "La Liga"
```

## 📊 Format des Données de Prédiction

Les prédictions sont maintenant stockées dans un format "long", où chaque ligne représente une analyse pour un type de pari spécifique.

| Colonne | Description |
|---|---|
| `date` | Date de l'analyse |
| `match_time` | Date et heure du match |
| `fixture_id` | ID unique du match |
| `league_name` | Nom de la ligue |
| `home_team` | Équipe à domicile |
| `away_team` | Équipe à l'extérieur |
| `bet_type` | Type de pari (ex: `Correct Score`) |
| `bet_value` | Valeur du pari (ex: `2-1`) |
| `target_odd` | Cote moyenne pour ce pari au moment de l'analyse |
| `similarity_pct` | Pourcentage de matchs historiques avec une cote similaire |
| `similar_matches_count` | Nombre total de matchs similaires trouvés |
| `similarity_reference_count` | Nombre de matchs dans l'historique utilisés pour la comparaison |

## 📈 Métriques d'Analyse

### `similarity_pct` (Pourcentage de Similarité)
Cette métrique indique la proportion de matchs dans notre base de données historique qui avaient une cote similaire pour un pari donné. Un pourcentage élevé signifie que la cote actuelle n'est pas rare.

### `similarity_reference_count` (Nombre de Références Similaires)
C'est le nombre brut de matchs historiques qui ont été considérés comme "similaires". Cette métrique donne une indication du volume de données qui soutient le `similarity_pct`. **Attention :** un grand nombre de références ne garantit pas la probabilité du résultat, mais indique plutôt la fréquence d'une cote similaire.

## 🔧 Configuration Avancée

### Paramètres dans `src/prediction/daily_predictions_workflow.py`

```python
self.SIMILARITY_THRESHOLD = 0.15        # Seuil de similarité des cotes
self.MIN_BOOKMAKERS_THRESHOLD = 2       # Minimum de bookmakers requis
```

### Ligues Supportées

| Code | Ligue | Pays |
|------|-------|------|
| ENG1 | Premier League | Angleterre |
| FRA1 | Ligue 1 | France |
| ITA1 | Serie A | Italie |
| GER1 | Bundesliga | Allemagne |
| SPA1 | La Liga | Espagne |
| NED1 | Eredivisie | Pays-Bas |
| POR1 | Primeira Liga | Portugal |
| BEL1 | Jupiler Pro League | Belgique |
| ENG2 | Championship | Angleterre |
| FRA2 | Ligue 2 | France |
| ITA2 | Serie B | Italie |
| GER2 | 2. Bundesliga | Allemagne |
| SPA2 | Segunda División | Espagne |
| TUR1 | Süper Lig | Turquie |
| SAU1 | Saudi Pro League | Arabie Saoudite |

## 📱 Service Systemd (Production)

Pour une installation en production :

```bash
# Générer le fichier de service
python3 setup_predictions_system.py

# Installer le service
sudo cp /tmp/football-predictions.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable football-predictions
sudo systemctl start football-predictions

# Vérifier le statut
sudo systemctl status football-predictions
```

## 🚨 Résolution de Problèmes

### Erreur "Clé API manquante"
```bash
export RAPIDAPI_KEY='your_key_here'
# Ou ajoutez-la à votre .bashrc/.zshrc
```

### Erreur "Données historiques manquantes"
```bash
# Lancez d'abord les collecteurs existants
python3 src/data_processing/football_data_updater.py
python3 src/data_processing/football_odds_collector.py
```

### Erreur "Aucun match trouvé"
- Vérifiez que l'API est accessible
- Assurez-vous que la date correspond à des jours de matchs
- Vérifiez les logs pour plus de détails

## 📊 Exemples d'Analyses

### Prédictions Haute Confiance

```bash
# Trouver les prédictions avec >80% de confiance
PYTHONPATH=src python3 src/analysis/predictions_analyzer.py | grep "HAUTE CONFIANCE"
```

### Analyses par Ligue

```bash
# Statistiques par ligue
PYTHONPATH=src python3 src/analysis/predictions_analyzer.py | grep "ANALYSE PAR LIGUE"
```

### Export de Données

```bash
# Exporter les données de janvier 2025
PYTHONPATH=src python3 src/analysis/predictions_analyzer.py --export --date-from 2025-01-01 --date-to 2025-01-31
```

## 📝 Logs

Les logs sont sauvegardés dans :
- `daily_predictions.log` : Logs du workflow principal
- `scheduler_predictions.log` : Logs du scheduler
- Console : Affichage en temps réel

## 🤝 Intégration avec le Système Existant

Ce système s'intègre parfaitement avec votre infrastructure existante :
- Utilise les mêmes données collectées par vos scripts actuels
- Même configuration API et même structure de dossiers
- Compatible avec les horaires de vos collecteurs existants

## 🎯 Prochaines Améliorations

- Interface web pour visualisation
- Notifications par email/Slack
- API REST pour accès programmatique
- Modèles d'apprentissage automatique avancés
- Intégration avec bases de données externes

## 🏅 Système de Classement Elo

En plus de l'analyse de similarité des cotes, ce projet inclut maintenant un système de classement Elo pour évaluer la force relative des équipes.

### Fonctionnement
- Chaque équipe de chaque ligue se voit attribuer un score Elo initial.
- Après chaque match, les scores Elo des deux équipes sont ajustés en fonction du résultat du match et de la différence de leur score Elo avant le match.
- Le calcul est effectué de manière chronologique sur tous les matchs des 365 derniers jours.

### Fichier de Données
Les classements Elo sont stockés dans `data/elo_ratings.csv` et mis à jour régulièrement.

### Utilisation
Le script `src/analysis/elo_calculator.py` peut être exécuté pour recalculer les scores Elo à partir des données de matchs existantes.

```bash
python3 src/analysis/elo_calculator.py
```

### Prédictions Basées sur l'Elo
Un workflow quotidien génère des prédictions basées uniquement sur le classement Elo des équipes.

**Fichiers Générés:**
- `data/predictions/daily_elo_predictions_YYYY-MM-DD.csv`: Contient les prédictions Elo pour les matchs du jour.
- `data/predictions/historical_elo_predictions.csv`: Archive toutes les prédictions Elo générées.

**Format du CSV:**
| Colonne | Description |
|---|---|
| `fixture_id` | ID unique du match |
| `date` | Date de la prédiction |
| `league_name` | Nom de la ligue |
| `home_team` | Équipe à domicile |
| `away_team` | Équipe à l'extérieur |
| `home_team_elo` | Classement Elo de l'équipe à domicile |
| `away_team_elo` | Classement Elo de l'équipe à l'extérieur |
| `home_win_probability` | Probabilité de victoire de l'équipe à domicile |
| `away_win_probability` | Probabilité de victoire de l'équipe à l'extérieur |
| `draw_probability` | Probabilité de match nul |
| `home_win_odds` | Cote implicite pour la victoire à domicile |
| `away_win_odds` | Cote implicite pour la victoire à l'extérieur |
| `draw_odds` | Cote implicite pour le match nul |

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs
2. Lancez `python3 quick_start.py --status`
3. Utilisez le mode test : `python3 quick_start.py --test`

---

*Système développé pour l'analyse prédictive robuste basée sur 15 ligues européennes et saoudiennes* ⚽
