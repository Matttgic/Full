import requests
import pandas as pd
import os
import time
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional, Set
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('football_odds.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompleteFootballOddsCollector:
    """
    Collecteur COMPLET de toutes les cotes historiques disponibles
    Récupère TOUS les marchés, TOUS les bookmakers, TOUTES les valeurs
    """
    
    def __init__(self, rapidapi_key: str):
        """
        Initialise le collecteur avec la clé RapidAPI
        
        Args:
            rapidapi_key (str): Clé d'API RapidAPI
        """
        self.api_key = rapidapi_key
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com',
            'x-rapidapi-key': self.api_key
        }
        
        # Configuration de toutes les ligues
        self.all_leagues = {
            # Big 5
            'ENG1': {'id': 39, 'name': 'Premier League', 'country': 'England'},
            'FRA1': {'id': 61, 'name': 'Ligue 1', 'country': 'France'},
            'ITA1': {'id': 135, 'name': 'Serie A', 'country': 'Italy'},
            'GER1': {'id': 78, 'name': 'Bundesliga', 'country': 'Germany'},
            'SPA1': {'id': 140, 'name': 'La Liga', 'country': 'Spain'},
            # Nouvelles ligues
            'NED1': {'id': 88, 'name': 'Eredivisie', 'country': 'Netherlands'},
            'POR1': {'id': 94, 'name': 'Primeira Liga', 'country': 'Portugal'},
            'BEL1': {'id': 144, 'name': 'Jupiler Pro League', 'country': 'Belgium'},
            'ENG2': {'id': 40, 'name': 'Championship', 'country': 'England'},
            'FRA2': {'id': 62, 'name': 'Ligue 2', 'country': 'France'},
            'ITA2': {'id': 136, 'name': 'Serie B', 'country': 'Italy'},
            'GER2': {'id': 79, 'name': '2. Bundesliga', 'country': 'Germany'},
            'SPA2': {'id': 141, 'name': 'Segunda División', 'country': 'Spain'},
            'TUR1': {'id': 203, 'name': 'Süper Lig', 'country': 'Turkey'},
            'SAU1': {'id': 307, 'name': 'Saudi Pro League', 'country': 'Saudi Arabia'}
        }
        
        # Configuration des dates - 365 derniers jours
        self.end_date = datetime.now().date()
        self.start_date = self.end_date - timedelta(days=365)
        
        # Saisons à analyser
        self.seasons_to_collect = [2024, 2025, 2026]  # Incluant 2026 pour les nouvelles saisons
        
        # Sets pour collecter dynamiquement tous les bookmakers et marchés
        self.discovered_bookmakers: Set[str] = set()
        self.discovered_bet_types: Dict[int, str] = {}
        self.discovered_bet_values: Set[str] = set()
        
        # Création du dossier odds avec sous-dossiers
        self.odds_folder = "complete_odds_data"
        self.summary_folder = os.path.join(self.odds_folder, "summaries")
        self.raw_folder = os.path.join(self.odds_folder, "raw_data")
        
        for folder in [self.odds_folder, self.summary_folder, self.raw_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
                logger.info(f"Dossier '{folder}' créé")
        
        # Statistiques globales
        self.global_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_odds_collected': 0,
            'matches_with_odds': set(),
            'collection_start_time': None,
            'collection_end_time': None
        }
    
    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Effectue une requête à l'API avec gestion d'erreurs avancée et retry intelligent
        """
        url = f"{self.base_url}/{endpoint}"
        max_retries = 5
        base_wait_time = 2
        
        self.global_stats['total_requests'] += 1
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"🔄 Requête API (tentative {attempt + 1}): {endpoint}")
                
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=45  # Timeout plus long pour les odds
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        results_count = data.get('results', 0)
                        
                        if results_count > 0:
                            logger.debug(f"✅ Succès - {results_count} résultats")
                            self.global_stats['successful_requests'] += 1
                            return data
                        else:
                            logger.debug(f"⚠️ Réponse vide pour {endpoint}")
                            return data  # Retourner quand même pour traitement
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Erreur JSON: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(base_wait_time * (attempt + 1))
                            continue
                        
                elif response.status_code == 429:  # Rate limit
                    wait_time = min(60, base_wait_time * (2 ** attempt))  # Exponential backoff, max 60s
                    logger.warning(f"⏳ Rate limit - attente {wait_time}s (tentative {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                    
                elif response.status_code in [500, 502, 503, 504]:  # Erreurs serveur
                    wait_time = base_wait_time * (attempt + 1)
                    logger.warning(f"🔧 Erreur serveur {response.status_code} - attente {wait_time}s")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                        
                else:
                    logger.error(f"❌ Erreur HTTP {response.status_code}: {response.text[:200]}")
                    if attempt < max_retries - 1:
                        time.sleep(base_wait_time * (attempt + 1))
                        continue
                    
            except requests.exceptions.Timeout:
                wait_time = base_wait_time * (attempt + 1)
                logger.warning(f"⏰ Timeout - attente {wait_time}s (tentative {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                    
            except requests.exceptions.ConnectionError:
                wait_time = base_wait_time * (attempt + 1)
                logger.warning(f"🔌 Erreur de connexion - attente {wait_time}s")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Erreur inattendue: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_wait_time)
                    continue
        
        self.global_stats['failed_requests'] += 1
        return None
    
    def load_existing_fixtures(self, league_code: str) -> List[int]:
        """
        Charge les IDs des matchs existants depuis les fichiers CSV des matchs
        Avec vérification intelligente des données manquantes
        """
        data_folder = "data"
        filepath = os.path.join(data_folder, f"{league_code}.csv")
        
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                if 'fixture_id' in df.columns:
                    # Filtrer pour les 365 derniers jours
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce').dt.date
                        df_filtered = df[df['date'] >= self.start_date]
                        
                        # Priorité aux matchs terminés (plus de chances d'avoir des odds)
                        if 'status_short' in df_filtered.columns:
                            finished_matches = df_filtered[df_filtered['status_short'] == 'FT']['fixture_id'].tolist()
                            other_matches = df_filtered[df_filtered['status_short'] != 'FT']['fixture_id'].tolist()
                            fixture_ids = finished_matches + other_matches
                        else:
                            fixture_ids = df_filtered['fixture_id'].tolist()
                        
                        # Nettoyer et convertir en int
                        fixture_ids = [int(x) for x in fixture_ids if pd.notna(x)]
                        
                        logger.info(f"📂 {len(fixture_ids)} matchs chargés depuis {filepath}")
                        if finished_matches:
                            logger.info(f"   🏁 {len(finished_matches)} matchs terminés prioritaires")
                        return fixture_ids
                    else:
                        fixture_ids = [int(x) for x in df['fixture_id'].dropna() if pd.notna(x)]
                        logger.info(f"📂 {len(fixture_ids)} matchs chargés (sans filtre date)")
                        return fixture_ids
                else:
                    logger.warning(f"⚠️ Colonne 'fixture_id' manquante dans {filepath}")
                    return []
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement de {filepath}: {e}")
                return []
        else:
            logger.info(f"📂 Fichier {filepath} non trouvé - récupération via API")
            return []
    
    def get_league_fixtures_for_odds(self, league_id: int) -> List[Dict]:
        """
        Récupère TOUS les matchs d'une ligue avec stratégie optimisée
        """
        logger.info(f"🔄 Récupération matchs pour odds - ligue {league_id}")
        
        all_fixtures = []
        
        # Stratégie multi-saisons avec gestion d'erreurs
        for season in self.seasons_to_collect:
            logger.info(f"📅 Saison {season}")
            
            # Requête principale pour la saison
            params = {
                'league': league_id,
                'season': season
            }
            
            data = self.make_api_request('fixtures', params)
            
            if data and 'response' in data:
                season_fixtures = data['response']
                logger.info(f"✅ {len(season_fixtures)} matchs saison {season}")
                all_fixtures.extend(season_fixtures)
            else:
                logger.warning(f"❌ Échec saison {season}")
            
            # Pause adaptative entre saisons
            time.sleep(1.5)
        
        # Filtrage intelligent par date
        filtered_fixtures = []
        dates_found = []
        
        for fixture in all_fixtures:
            fixture_date_str = fixture.get('fixture', {}).get('date', '')
            
            if fixture_date_str:
                try:
                    fixture_date = datetime.fromisoformat(
                        fixture_date_str.replace('Z', '+00:00')
                    ).date()
                    dates_found.append(fixture_date)
                    
                    if self.start_date <= fixture_date <= self.end_date:
                        filtered_fixtures.append(fixture)
                        
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Erreur parsing date '{fixture_date_str}': {e}")
                    # Garder le match en cas d'erreur de date
                    filtered_fixtures.append(fixture)
        
        # Statistiques des données
        if dates_found:
            min_date, max_date = min(dates_found), max(dates_found)
            logger.info(f"📅 Période données: {min_date} à {max_date}")
        
        logger.info(f"📊 Total après filtrage: {len(filtered_fixtures)} matchs")
        return filtered_fixtures
    
    def get_complete_fixture_odds(self, fixture_id: int) -> Optional[List[Dict]]:
        """
        Récupère TOUTES les cotes disponibles pour un match
        Utilise TOUTES les stratégies possibles pour maximiser la collecte
        """
        all_odds_data = []
        strategies_used = []
        
        # Stratégie 1: Requête générale complète (TOUS les bookmakers, TOUS les marchés)
        params_general = {'fixture': fixture_id}
        data_general = self.make_api_request('odds', params_general)
        
        if data_general and 'response' in data_general and data_general['response']:
            all_odds_data.extend(data_general['response'])
            strategies_used.append(f"Général: {len(data_general['response'])}")
            logger.debug(f"✅ Stratégie générale: {len(data_general['response'])} entrées")
        
        # Stratégie 2: Cotes live/en direct
        params_live = {'fixture': fixture_id}
        data_live = self.make_api_request('odds/live', params_live)
        
        if data_live and 'response' in data_live and data_live['response']:
            # Fusionner sans doublons basés sur bookmaker + bet_type + value
            live_added = 0
            for live_entry in data_live['response']:
                # Vérifier si cette entrée existe déjà dans les données générales
                is_duplicate = False
                for existing_entry in all_odds_data:
                    if (existing_entry.get('fixture', {}).get('id') == live_entry.get('fixture', {}).get('id') and
                        str(existing_entry) == str(live_entry)):  # Comparaison simple
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    all_odds_data.append(live_entry)
                    live_added += 1
            
            if live_added > 0:
                strategies_used.append(f"Live: +{live_added}")
                logger.debug(f"✅ Stratégie live: {live_added} nouvelles entrées")
        
        # Stratégie 3: Requêtes par bookmaker spécifique pour maximiser la couverture
        # (Essayer quelques bookmakers principaux individuellement)
        major_bookmaker_ids = [8, 11, 16]  # Bet365, William Hill, Unibet (IDs courants)
        
        for bookmaker_id in major_bookmaker_ids:
            params_bookmaker = {
                'fixture': fixture_id,
                'bookmaker': bookmaker_id
            }
            
            data_bookmaker = self.make_api_request('odds', params_bookmaker)
            
            if data_bookmaker and 'response' in data_bookmaker and data_bookmaker['response']:
                # Ajouter seulement les nouvelles données
                bookmaker_added = 0
                for bm_entry in data_bookmaker['response']:
                    # Vérification de doublons simplifiée
                    entry_key = f"{bm_entry.get('fixture', {}).get('id')}_{bookmaker_id}"
                    existing_keys = [f"{e.get('fixture', {}).get('id')}_{bm.get('id', 0)}" 
                                   for e in all_odds_data 
                                   for bm in e.get('bookmakers', [])]
                    
                    if entry_key not in existing_keys:
                        all_odds_data.append(bm_entry)
                        bookmaker_added += 1
                
                if bookmaker_added > 0:
                    strategies_used.append(f"BM{bookmaker_id}: +{bookmaker_added}")
                    logger.debug(f"✅ Bookmaker {bookmaker_id}: {bookmaker_added} nouvelles entrées")
            
            time.sleep(0.3)  # Petite pause entre bookmakers
        
        # Stratégie 4: Requêtes par type de pari majeur
        major_bet_types = [1, 3, 5, 8, 12]  # 1X2, O/U, BTTS, Handicap, Double Chance
        
        for bet_type_id in major_bet_types:
            params_bet = {
                'fixture': fixture_id,
                'bet': bet_type_id
            }
            
            data_bet = self.make_api_request('odds', params_bet)
            
            if data_bet and 'response' in data_bet and data_bet['response']:
                bet_added = 0
                for bet_entry in data_bet['response']:
                    # Vérification simplifiée des doublons par bet_type
                    is_new = True
                    for existing in all_odds_data:
                        for existing_bm in existing.get('bookmakers', []):
                            for existing_bet in existing_bm.get('bets', []):
                                if existing_bet.get('id') == bet_type_id:
                                    is_new = False
                                    break
                    
                    if is_new:
                        all_odds_data.append(bet_entry)
                        bet_added += 1
                
                if bet_added > 0:
                    strategies_used.append(f"Bet{bet_type_id}: +{bet_added}")
                    logger.debug(f"✅ Type pari {bet_type_id}: {bet_added} nouvelles entrées")
            
            time.sleep(0.2)  # Pause entre types de paris
        
        # Log du résumé des stratégies
        if strategies_used:
            logger.info(f"🎯 Match {fixture_id}: {len(all_odds_data)} entrées totales ({', '.join(strategies_used)})")
        
        # Pause finale pour respecter les limites d'API
        time.sleep(1.0)
        
        return all_odds_data if all_odds_data else None
    
    def process_complete_odds_data(self, fixture_id: int, odds_data: List[Dict]) -> List[Dict]:
        """
        Traite COMPLÈTEMENT toutes les données de cotes
        Capture TOUS les bookmakers, marchés et valeurs
        """
        processed_odds = []
        
        if not odds_data:
            return processed_odds
        
        for odds_entry in odds_data:
            try:
                # Informations de base du match
                fixture_info = odds_entry.get('fixture', {})
                league_info = odds_entry.get('league', {})
                
                base_info = {
                    'fixture_id': fixture_id,
                    'fixture_date': fixture_info.get('date'),
                    'fixture_timestamp': fixture_info.get('timestamp'),
                    'fixture_timezone': fixture_info.get('timezone'),
                    'fixture_status': fixture_info.get('status', {}).get('short'),
                    'league_id': league_info.get('id'),
                    'league_name': league_info.get('name'),
                    'league_country': league_info.get('country'),
                    'season': league_info.get('season'),
                    'round': league_info.get('round')
                }
                
                # Traitement de TOUS les bookmakers
                bookmakers = odds_entry.get('bookmakers', [])
                
                for bookmaker in bookmakers:
                    bookmaker_name = bookmaker.get('name', 'Unknown')
                    bookmaker_id = bookmaker.get('id')
                    
                    # Collecter tous les bookmakers découverts
                    self.discovered_bookmakers.add(bookmaker_name)
                    
                    # Informations bookmaker
                    bookmaker_info = {
                        'bookmaker_id': bookmaker_id,
                        'bookmaker_name': bookmaker_name
                    }
                    
                    # Traitement de TOUS les types de paris
                    bets = bookmaker.get('bets', [])
                    
                    for bet in bets:
                        bet_id = bet.get('id')
                        bet_name = bet.get('name', 'Unknown Bet')
                        
                        # Collecter tous les types de paris découverts
                        if bet_id:
                            self.discovered_bet_types[bet_id] = bet_name
                        
                        # Informations du pari
                        bet_info = {
                            'bet_type_id': bet_id,
                            'bet_type_name': bet_name
                        }
                        
                        # Traitement de TOUTES les valeurs/outcomes
                        values = bet.get('values', [])
                        
                        for value in values:
                            bet_value = value.get('value', 'Unknown')
                            odd = value.get('odd')
                            handicap = value.get('handicap')  # Pour les paris avec handicap
                            over = value.get('over')  # Pour Over/Under
                            under = value.get('under')  # Pour Over/Under
                            
                            # Collecter toutes les valeurs découvertes
                            self.discovered_bet_values.add(bet_value)
                            
                            # Créer l'enregistrement complet
                            odds_record = {**base_info, **bookmaker_info, **bet_info}
                            odds_record.update({
                                'bet_value': bet_value,
                                'odd': float(odd) if odd and odd != 'null' else None,
                                'handicap': handicap if handicap and handicap != 'null' else None,
                                'over': over if over and over != 'null' else None,
                                'under': under if under and under != 'null' else None,
                                'collected_at': datetime.now().isoformat(),
                                'collection_date': datetime.now().date().isoformat()
                            })
                            
                            processed_odds.append(odds_record)
                            self.global_stats['total_odds_collected'] += 1
                
            except Exception as e:
                logger.error(f"❌ Erreur traitement odds entry: {e}")
                continue
        
        if processed_odds:
            self.global_stats['matches_with_odds'].add(fixture_id)
        
        return processed_odds
    
    def collect_complete_league_odds(self, league_code: str) -> pd.DataFrame:
        """
        Collecte TOUTES les cotes d'une ligue avec stratégie optimisée
        """
        league_info = self.all_leagues[league_code]
        league_id = league_info['id']
        
        logger.info(f"🎯 COLLECTE COMPLÈTE des odds pour {league_info['name']} ({league_code})")
        logger.info(f"   📊 Cible: TOUS les marchés, TOUS les bookmakers")
        
        # Chargement des matchs avec priorité aux données existantes
        fixture_ids = self.load_existing_fixtures(league_code)
        
        # Si pas de matchs locaux, récupérer via API
        if not fixture_ids:
            logger.info("🌐 Récupération matchs via API...")
            fixtures = self.get_league_fixtures_for_odds(league_id)
            fixture_ids = [
                f.get('fixture', {}).get('id') 
                for f in fixtures 
                if f.get('fixture', {}).get('id')
            ]
        
        if not fixture_ids:
            logger.warning(f"❌ Aucun match trouvé pour {league_code}")
            return pd.DataFrame()
        
        logger.info(f"📊 {len(fixture_ids)} matchs à analyser pour odds complètes")
        
        # Collections pour cette ligue
        all_league_odds = []
        league_stats = {
            'matches_processed': 0,
            'matches_with_odds': 0,
            'matches_without_odds': 0,
            'total_odds_found': 0,
            'bookmakers_found': set(),
            'bet_types_found': set()
        }
        
        # Traitement avec gestion avancée des erreurs
        batch_size = 25  # Plus petit batch pour éviter les timeouts
        total_batches = (len(fixture_ids) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(fixture_ids))
            batch_fixture_ids = fixture_ids[start_idx:end_idx]
            
            logger.info(f"📦 Batch {batch_num + 1}/{total_batches}: matchs {start_idx + 1}-{end_idx}")
            
            for i, fixture_id in enumerate(batch_fixture_ids):
                try:
                    current_match = start_idx + i + 1
                    logger.info(f"🎲 Match {current_match}/{len(fixture_ids)} - ID: {fixture_id}")
                    
                    # Récupération complète des odds
                    odds_data = self.get_complete_fixture_odds(fixture_id)
                    
                    league_stats['matches_processed'] += 1
                    
                    if odds_data:
                        # Traitement complet des données
                        processed_odds = self.process_complete_odds_data(fixture_id, odds_data)
                        
                        if processed_odds:
                            all_league_odds.extend(processed_odds)
                            league_stats['matches_with_odds'] += 1
                            league_stats['total_odds_found'] += len(processed_odds)
                            
                            # Collecter les stats de cette ligue
                            for odd in processed_odds:
                                if odd.get('bookmaker_name'):
                                    league_stats['bookmakers_found'].add(odd['bookmaker_name'])
                                if odd.get('bet_type_name'):
                                    league_stats['bet_types_found'].add(odd['bet_type_name'])
                            
                            logger.info(f"   ✅ {len(processed_odds)} cotes récupérées")
                        else:
                            league_stats['matches_without_odds'] += 1
                            logger.debug(f"   ⚠️ Données odds vides après traitement")
                    else:
                        league_stats['matches_without_odds'] += 1
                        logger.debug(f"   ❌ Aucune donnée odds récupérée")
                    
                    # Pause adaptative basée sur le succès
                    if odds_data and processed_odds:
                        time.sleep(1.0)  # Pause courte si succès
                    else:
                        time.sleep(0.5)  # Pause plus courte si échec
                        
                except Exception as e:
                    league_stats['matches_without_odds'] += 1
                    logger.error(f"❌ Erreur match {fixture_id}: {e}")
                    time.sleep(0.5)
                    continue
            
            # Pause entre batches avec feedback
            if batch_num < total_batches - 1:
                logger.info(f"⏳ Pause 8s... (Progress: {league_stats['matches_with_odds']}/{league_stats['matches_processed']} matchs avec odds)")
                time.sleep(8)
        
        # Création du DataFrame final
        if all_league_odds:
            df = pd.DataFrame(all_league_odds)
            
            # Rapport détaillé pour cette ligue
            logger.info(f"🎉 COLLECTE TERMINÉE pour {league_code}:")
            logger.info(f"   📊 Total cotes collectées: {len(df):,}")
            logger.info(f"   🏟️ Matchs traités: {league_stats['matches_processed']}")
            logger.info(f"   ✅ Matchs avec odds: {league_stats['matches_with_odds']}")
            logger.info(f"   ❌ Matchs sans odds: {league_stats['matches_without_odds']}")
            logger.info(f"   📚 Bookmakers trouvés: {len(league_stats['bookmakers_found'])}")
            logger.info(f"   🎲 Types de paris: {len(league_stats['bet_types_found'])}")
            
            # Top 5 bookmakers pour cette ligue
            if 'bookmaker_name' in df.columns:
                top_bookmakers = df['bookmaker_name'].value_counts().head(5)
                logger.info(f"   🏆 Top bookmakers:")
                for bm, count in top_bookmakers.items():
                    logger.info(f"      - {bm}: {count:,} cotes")
            
            return df
        else:
            logger.warning(f"❌ AUCUNE COTE collectée pour {league_code}")
            return pd.DataFrame()
    
    def save_complete_odds(self, df: pd.DataFrame, league_code: str) -> None:
        """
        Sauvegarde complète avec fichiers multiples et résumés
        """
        if df.empty:
            logger.warning(f"❌ Aucune donnée pour {league_code}")
            return
        
        league_info = self.all_leagues[league_code]
        
        try:
            # 1. Fichier principal complet
            main_filename = f"{league_code}_complete_odds.csv"
            main_filepath = os.path.join(self.raw_folder, main_filename)
            
            # Tri optimisé
            sort_columns = []
            for col in ['fixture_date', 'fixture_id', 'bookmaker_name', 'bet_type_id']:
                if col in df.columns:
                    sort_columns.append(col)
            
            if sort_columns:
                df_sorted = df.sort_values(sort_columns)
            else:
                df_sorted = df
            
            # Sauvegarde principale
            df_sorted.to_csv(main_filepath, index=False, encoding='utf-8')
            logger.info(f"💾 Fichier principal: {main_filepath} ({len(df):,} lignes)")
            
            # 2. Résumé par bookmaker
            if 'bookmaker_name' in df.columns:
                bookmaker_summary = df.groupby('bookmaker_name').agg({
                    'fixture_id': 'nunique',
                    'bet_type_id': 'nunique',
                    'odd': ['count', 'mean', 'min', 'max']
                }).round(3)
                
                bookmaker_summary.columns = ['unique_matches', 'unique_bet_types', 'total_odds', 'avg_odd', 'min_odd', 'max_odd']
                bookmaker_summary = bookmaker_summary.reset_index()
                
                bookmaker_file = f"{league_code}_bookmaker_summary.csv"
                bookmaker_path = os.path.join(self.summary_folder, bookmaker_file)
                bookmaker_summary.to_csv(bookmaker_path, index=False)
                logger.info(f"📊 Résumé bookmakers: {bookmaker_path}")
            
            # 3. Résumé par type de pari
            if 'bet_type_name' in df.columns:
                bet_type_summary = df.groupby(['bet_type_id', 'bet_type_name']).agg({
                    'fixture_id': 'nunique',
                    'bookmaker_name': 'nunique',
                    'odd': ['count', 'mean', 'std']
                }).round(3)
                
                bet_type_summary.columns = ['unique_matches', 'unique_bookmakers', 'total_odds', 'avg_odd', 'std_odd']
                bet_type_summary = bet_type_summary.reset_index()
                
                bet_type_file = f"{league_code}_bet_types_summary.csv"
                bet_type_path = os.path.join(self.summary_folder, bet_type_file)
                bet_type_summary.to_csv(bet_type_path, index=False)
                logger.info(f"🎲 Résumé types paris: {bet_type_path}")
            
            # 4. Statistiques du fichier
            file_stats = {
                'league_code': league_code,
                'league_name': league_info['name'],
                'total_odds': len(df),
                'unique_matches': df['fixture_id'].nunique() if 'fixture_id' in df.columns else 0,
                'unique_bookmakers': df['bookmaker_name'].nunique() if 'bookmaker_name' in df.columns else 0,
                'unique_bet_types': df['bet_type_id'].nunique() if 'bet_type_id' in df.columns else 0,
                'date_range_start': df['fixture_date'].min() if 'fixture_date' in df.columns else None,
                'date_range_end': df['fixture_date'].max() if 'fixture_date' in df.columns else None,
                'file_size_mb': round(os.path.getsize(main_filepath) / (1024 * 1024), 2),
                'created_at': datetime.now().isoformat()
            }
            
            # Affichage des statistiques
            logger.info(f"📈 STATISTIQUES {league_code}:")
            logger.info(f"   📊 Total cotes: {file_stats['total_odds']:,}")
            logger.info(f"   🏟️ Matchs uniques: {file_stats['unique_matches']:,}")
            logger.info(f"   📚 Bookmakers uniques: {file_stats['unique_bookmakers']:,}")
            logger.info(f"   🎲 Types de paris uniques: {file_stats['unique_bet_types']:,}")
            logger.info(f"   📅 Période: {file_stats['date_range_start']} à {file_stats['date_range_end']}")
            logger.info(f"   💾 Taille fichier: {file_stats['file_size_mb']} MB")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde de {league_code}: {e}")
    
    def run_complete_odds_collection(self) -> None:
        """
        Lance la collecte COMPLÈTE des odds pour toutes les ligues
        """
        logger.info("🚀 === DÉBUT DE LA COLLECTE COMPLÈTE DES ODDS ===")
        logger.info(f"📅 Période: {self.start_date} à {self.end_date} (365 derniers jours)")
        logger.info(f"🏆 Ligues: {len(self.all_leagues)} ligues configurées")
        logger.info(f"🎯 Objectif: TOUS les bookmakers, TOUS les marchés, TOUTES les valeurs")
        
        self.global_stats['collection_start_time'] = datetime.now()
        successful_collections = 0
        total_odds_collected = 0
        
        for i, league_code in enumerate(self.all_leagues.keys()):
            try:
                logger.info(f"\n🏟️ --- Collecte odds {i+1}/{len(self.all_leagues)}: {league_code} ---")
                
                # Collecte complète des odds
                df = self.collect_complete_league_odds(league_code)
                
                # Sauvegarde avec résumés
                if not df.empty:
                    self.save_complete_odds(df, league_code)
                    successful_collections += 1
                    total_odds_collected += len(df)
                else:
                    logger.warning(f"⚠️ Aucune cote collectée pour {league_code}")
                
                # Pause entre les ligues pour respecter l'API
                if i < len(self.all_leagues) - 1:  # Pas de pause après la dernière ligue
                    logger.info("⏱️ Pause de 15 secondes avant la prochaine ligue...")
                    time.sleep(15)
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de la collecte des odds de {league_code}: {e}")
                continue
        
        self.global_stats['collection_end_time'] = datetime.now()
        duration = self.global_stats['collection_end_time'] - self.global_stats['collection_start_time']
        
        # Rapport final détaillé
        logger.info(f"\n🎉 === COLLECTE COMPLÈTE DES ODDS TERMINÉE ===")
        logger.info(f"⏱️ Durée totale: {duration}")
        logger.info(f"✅ Ligues traitées avec succès: {successful_collections}/{len(self.all_leagues)}")
        logger.info(f"🎲 Total odds collectées: {total_odds_collected:,}")
        logger.info(f"🏟️ Total matchs avec odds: {len(self.global_stats['matches_with_odds'])}")
        
        # Statistiques globales de l'API
        logger.info(f"📊 Statistiques API:")
        logger.info(f"   📡 Requêtes totales: {self.global_stats['total_requests']}")
        logger.info(f"   ✅ Requêtes réussies: {self.global_stats['successful_requests']}")
        logger.info(f"   ❌ Requêtes échouées: {self.global_stats['failed_requests']}")
        
        success_rate = (self.global_stats['successful_requests'] / max(1, self.global_stats['total_requests'])) * 100
        logger.info(f"   📈 Taux de succès: {success_rate:.1f}%")
        
        # Résumé des découvertes
        logger.info(f"🔍 Découvertes globales:")
        logger.info(f"   📚 Bookmakers découverts: {len(self.discovered_bookmakers)}")
        logger.info(f"   🎲 Types de paris découverts: {len(self.discovered_bet_types)}")
        logger.info(f"   🎯 Valeurs de paris découvertes: {len(self.discovered_bet_values)}")
        
        # Top bookmakers découverts
        if self.discovered_bookmakers:
            logger.info(f"   🏆 Bookmakers trouvés: {', '.join(sorted(list(self.discovered_bookmakers))[:10])}")
        
        # Taille totale des fichiers générés
        total_size = 0
        if os.path.exists(self.raw_folder):
            csv_files = [f for f in os.listdir(self.raw_folder) if f.endswith('.csv')]
            logger.info(f"📊 Fichiers CSV créés: {len(csv_files)}")
            
            for file in csv_files:
                filepath = os.path.join(self.raw_folder, file)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
            
            total_size_mb = total_size / (1024 * 1024)
            logger.info(f"💾 Taille totale des données: {total_size_mb:.2f} MB")
        
        # Sauvegarde des métadonnées globales
        self.save_global_metadata()
        
        logger.info(f"📁 Données complètes sauvegardées dans '{self.odds_folder}'")
        logger.info("🎯 Mission accomplie: TOUTES les cotes historiques disponibles collectées!")
    
    def save_global_metadata(self) -> None:
        """
        Sauvegarde les métadonnées globales de la collecte
        """
        try:
            metadata = {
                'collection_info': {
                    'start_time': self.global_stats['collection_start_time'].isoformat() if self.global_stats['collection_start_time'] else None,
                    'end_time': self.global_stats['collection_end_time'].isoformat() if self.global_stats['collection_end_time'] else None,
                    'duration_seconds': (self.global_stats['collection_end_time'] - self.global_stats['collection_start_time']).total_seconds() if self.global_stats['collection_start_time'] and self.global_stats['collection_end_time'] else 0,
                    'date_range_start': self.start_date.isoformat(),
                    'date_range_end': self.end_date.isoformat(),
                    'leagues_processed': len(self.all_leagues),
                    'total_odds_collected': self.global_stats['total_odds_collected'],
                    'matches_with_odds': len(self.global_stats['matches_with_odds'])
                },
                'api_statistics': {
                    'total_requests': self.global_stats['total_requests'],
                    'successful_requests': self.global_stats['successful_requests'],
                    'failed_requests': self.global_stats['failed_requests'],
                    'success_rate_percent': (self.global_stats['successful_requests'] / max(1, self.global_stats['total_requests'])) * 100
                },
                'discovered_data': {
                    'bookmakers': sorted(list(self.discovered_bookmakers)),
                    'bet_types': dict(self.discovered_bet_types),
                    'bet_values': sorted(list(self.discovered_bet_values)),
                    'total_bookmakers': len(self.discovered_bookmakers),
                    'total_bet_types': len(self.discovered_bet_types),
                    'total_bet_values': len(self.discovered_bet_values)
                },
                'leagues_info': self.all_leagues
            }
            
            # Sauvegarde en JSON
            metadata_file = os.path.join(self.odds_folder, 'collection_metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 Métadonnées sauvegardées: {metadata_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde métadonnées: {e}")

def main():
    """
    Fonction principale - Point d'entrée du script
    """
    import os
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        logger.error("⚠️ Clé RAPIDAPI_KEY non trouvée dans les variables d'environnement")
        logger.error("💡 Assurez-vous que le secret RAPIDAPI_KEY est configuré")
        return
    
    logger.info("✅ Clé API récupérée depuis les variables d'environnement")
    
    # Création du collecteur complet
    collector = CompleteFootballOddsCollector(RAPIDAPI_KEY)
    
    # Lancement de la collecte complète
    collector.run_complete_odds_collection()

if __name__ == "__main__":
    main() 
