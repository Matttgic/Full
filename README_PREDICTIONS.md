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
/app/
├── daily_predictions_workflow.py    # Script principal de prédictions
├── scheduler_predictions.py         # Scheduler automatique
├── predictions_analyzer.py          # Analyseur de résultats
├── setup_predictions_system.py      # Configuration système
├── quick_start.py                   # Démarrage rapide
├── requirements.txt                 # Dépendances Python
└── data/
    ├── predictions/                 # Fichiers de prédictions
    │   ├── daily_YYYY-MM-DD.csv     # CSV quotidiens
    │   └── historical_predictions.csv # Historique complet
    ├── odds/raw_data/               # Données de cotes (existant)
    └── matches/                     # Données de matchs (existant)
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
python3 setup_predictions_system.py
```

## 🎮 Utilisation

### Démarrage Rapide

```bash
# Test du système
python3 quick_start.py --test

# Exécution unique
python3 quick_start.py --run

# Démarrer le scheduler
python3 quick_start.py --schedule

# Analyser les résultats
python3 quick_start.py --analyze

# Vérifier le statut
python3 quick_start.py --status
```

### Utilisation Détaillée

#### 1. Workflow Quotidien

```bash
# Exécution manuelle du workflow
python3 daily_predictions_workflow.py
```

#### 2. Scheduler Automatique

```bash
# Démarrer le scheduler (reste en cours d'exécution)
python3 scheduler_predictions.py
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
python3 predictions_analyzer.py

# Rapport pour une date spécifique
python3 predictions_analyzer.py --date 2025-01-15

# Export filtré par ligues
python3 predictions_analyzer.py --export --league "Premier League" "La Liga"
```

## 📊 Format des Données CSV

### CSV Quotidien (`daily_YYYY-MM-DD.csv`)

| Colonne | Description |
|---------|-------------|
| `date` | Date des matchs |
| `match_time` | Heure du match |
| `fixture_id` | ID unique du match |
| `league_code` | Code de la ligue (ENG1, FRA1, etc.) |
| `league_name` | Nom complet de la ligue |
| `home_team` | Équipe domicile |
| `away_team` | Équipe extérieure |
| `{bet_type}_target_odd` | Cote actuelle pour ce type de pari |
| `{bet_type}_similarity_pct` | % de similarité basé sur l'historique |
| `{bet_type}_similar_matches` | Nombre de matchs similaires trouvés |
| `{bet_type}_confidence` | Score de confiance (0-100) |

### Types de Paris Analysés

- **Match Winner** : Victoire équipe domicile/extérieure/match nul
- **Over/Under** : Plus/moins de buts (toutes les valeurs)
- **Both Teams to Score** : Les deux équipes marquent
- **Double Chance** : Combinaisons de résultats
- **Correct Score** : Score exact
- **Half Time/Full Time** : Résultat mi-temps/fin de match
- **Total Goals** : Nombre total de buts
- **Corners** : Nombre de corners
- **Cards** : Nombre de cartons
- **Et bien d'autres...**

## 📈 Métriques de Confiance

### Pourcentage de Similarité
- **0-25%** : Faible similarité (peu de matchs historiques similaires)
- **25-50%** : Similarité modérée
- **50-75%** : Bonne similarité
- **75-100%** : Très haute similarité

### Score de Confiance
- Calculé selon le nombre de matchs similaires trouvés
- Plus il y a de données historiques, plus le score est élevé
- Score maximum de 100 atteint avec 50+ matchs similaires

## 🔧 Configuration Avancée

### Paramètres dans `daily_predictions_workflow.py`

```python
SIMILARITY_THRESHOLD = 0.15        # Seuil de similarité des cotes
MIN_BOOKMAKERS_THRESHOLD = 2       # Minimum de bookmakers requis
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
python3 football_data_updater.py
python3 football_odds_collector.py
```

### Erreur "Aucun match trouvé"
- Vérifiez que l'API est accessible
- Assurez-vous que la date correspond à des jours de matchs
- Vérifiez les logs pour plus de détails

## 📊 Exemples d'Analyses

### Prédictions Haute Confiance

```bash
# Trouver les prédictions avec >80% de confiance
python3 predictions_analyzer.py | grep "HAUTE CONFIANCE"
```

### Analyses par Ligue

```bash
# Statistiques par ligue
python3 predictions_analyzer.py | grep "ANALYSE PAR LIGUE"
```

### Export de Données

```bash
# Exporter les données de janvier 2025
python3 predictions_analyzer.py --export --date-from 2025-01-01 --date-to 2025-01-31
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

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs
2. Lancez `python3 quick_start.py --status`
3. Utilisez le mode test : `python3 quick_start.py --test`

---

*Système développé pour l'analyse prédictive robuste basée sur 15 ligues européennes et saoudiennes* ⚽