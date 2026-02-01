"""
WFCD (Warframe Community Developers) Relic Database.
Fetches and stores all relics with their rare drops from the WFCD API.
"""

import sqlite3
import os
import sys
import threading
import requests
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_dir


@dataclass
class RareItem:
    """A rare item that drops from relics."""
    item_name: str
    relic_era: str
    relic_name: str
    relic_full: str  # e.g., "Axi A1"
    is_vaulted: bool = False


class WFCDRelicDatabase:
    """Database for all Warframe relics and rare drops from WFCD API."""
    
    WFCD_RELICS_URL = "https://drops.warframestat.us/data/relics.json"
    WFCD_ALL_URL = "https://drops.warframestat.us/data/all.json"
    
    def __init__(self, db_name: str = "wfcd_relics.db"):
        self.db_path = os.path.join(get_db_dir(), db_name)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._get_conn()
        self._create_tables()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()
    
    def _create_tables(self):
        """Create database tables."""
        with self._lock:
            cursor = self.conn.cursor()
            
            # Relics table - all relics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    era TEXT NOT NULL,
                    name TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    is_vaulted INTEGER DEFAULT 0,
                    UNIQUE(era, name)
                )
            ''')
            
            # Relic rewards table - all drops from relics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS relic_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relic_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    chance_intact REAL,
                    chance_radiant REAL,
                    FOREIGN KEY (relic_id) REFERENCES relics(id)
                )
            ''')
            
            # Rare items view - just the rare drops
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rare_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    relic_era TEXT NOT NULL,
                    relic_name TEXT NOT NULL,
                    relic_full TEXT NOT NULL,
                    is_vaulted INTEGER DEFAULT 0,
                    UNIQUE(item_name, relic_full)
                )
            ''')
            
            # Prices table - cached warframe.market prices
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS item_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL UNIQUE,
                    url_name TEXT NOT NULL,
                    lowest_price INTEGER,
                    avg_price REAL,
                    volume INTEGER,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Item ducat values - actual per-item ducat values from WFCD
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS item_ducats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL UNIQUE,
                    ducats INTEGER NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Sync metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    id INTEGER PRIMARY KEY,
                    last_sync TEXT,
                    total_relics INTEGER,
                    total_rare_items INTEGER
                )
            ''')
            
            # Create indexes for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rare_item_name ON rare_items(item_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rare_relic ON rare_items(relic_full)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relic_rewards_rarity ON relic_rewards(rarity)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_item_prices_name ON item_prices(item_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_item_ducats_name ON item_ducats(item_name)')
            
            self.conn.commit()
    
    def sync_from_wfcd(self, progress_callback=None) -> dict:
        """
        Sync all relic data from WFCD API.
        Returns stats about the sync.
        """
        if progress_callback:
            progress_callback("Fetching relic data from WFCD...")
        
        try:
            response = requests.get(self.WFCD_RELICS_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise Exception(f"Failed to fetch WFCD data: {e}")
        
        relics_data = data.get('relics', [])
        
        if progress_callback:
            progress_callback(f"Processing {len(relics_data)} relic entries...")
        
        # Track unique relics and rare items
        relics_seen = {}
        rare_items = []
        
        with self._lock:
            cursor = self.conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM rare_items')
            cursor.execute('DELETE FROM relic_rewards')
            cursor.execute('DELETE FROM relics')
            
            for entry in relics_data:
                era = entry.get('tier', '')
                name = entry.get('relicName', '')
                state = entry.get('state', 'Intact')
                rewards = entry.get('rewards', [])
                
                if not era or not name:
                    continue
                
                full_name = f"{era} {name}"
                relic_key = f"{era}_{name}"
                
                # Insert relic if not seen
                if relic_key not in relics_seen:
                    cursor.execute(
                        'INSERT OR IGNORE INTO relics (era, name, full_name) VALUES (?, ?, ?)',
                        (era, name, full_name)
                    )
                    cursor.execute('SELECT id FROM relics WHERE era = ? AND name = ?', (era, name))
                    row = cursor.fetchone()
                    relics_seen[relic_key] = row['id'] if row else None
                
                relic_id = relics_seen[relic_key]
                
                # Process rewards
                for reward in rewards:
                    item_name = reward.get('itemName', '')
                    rarity = reward.get('rarity', '')
                    chance = reward.get('chance', 0)
                    
                    if not item_name:
                        continue
                    
                    # Store chance based on refinement state
                    if state == 'Intact':
                        cursor.execute('''
                            INSERT OR REPLACE INTO relic_rewards 
                            (relic_id, item_name, rarity, chance_intact)
                            VALUES (?, ?, ?, ?)
                        ''', (relic_id, item_name, rarity, chance))
                    elif state == 'Radiant':
                        cursor.execute('''
                            UPDATE relic_rewards SET chance_radiant = ?
                            WHERE relic_id = ? AND item_name = ?
                        ''', (chance, relic_id, item_name))
                    
                    # Track rare items (only from Intact to avoid duplicates)
                    if rarity == 'Rare' and state == 'Intact':
                        cursor.execute('''
                            INSERT OR IGNORE INTO rare_items 
                            (item_name, relic_era, relic_name, relic_full)
                            VALUES (?, ?, ?, ?)
                        ''', (item_name, era, name, full_name))
                        rare_items.append({
                            'item': item_name,
                            'relic': full_name
                        })
            
            # Update sync metadata
            total_relics = len(relics_seen)
            total_rare = len(rare_items)
            
            cursor.execute('''
                INSERT OR REPLACE INTO sync_metadata 
                (id, last_sync, total_relics, total_rare_items)
                VALUES (1, ?, ?, ?)
            ''', (datetime.now().isoformat(), total_relics, total_rare))
            
            self.conn.commit()
        
        if progress_callback:
            progress_callback(f"Synced {total_relics} relics, {total_rare} rare items")
        
        # Also sync ducat values
        if progress_callback:
            progress_callback("Syncing ducat values...")
        ducat_count = self.sync_ducat_values(progress_callback)
        
        return {
            'total_relics': total_relics,
            'total_rare_items': total_rare,
            'total_ducat_items': ducat_count,
            'last_sync': datetime.now().isoformat()
        }
    
    def sync_ducat_values(self, progress_callback=None) -> int:
        """
        Sync ducat values for prime items from WFCD warframe-items repository.
        Returns the number of items with ducat values synced.
        """
        # Categories in WFCD warframe-items that contain prime parts
        WFCD_ITEMS_BASE = "https://raw.githubusercontent.com/WFCD/warframe-items/master/data/json"
        CATEGORIES = [
            "Primary.json",
            "Secondary.json", 
            "Melee.json",
            "Warframes.json",
            "Sentinels.json",
            "Archwing.json",
        ]
        
        ducat_items = {}
        
        for category in CATEGORIES:
            url = f"{WFCD_ITEMS_BASE}/{category}"
            if progress_callback:
                progress_callback(f"Fetching ducat values from {category}...")
            
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                items = response.json()
                
                for item in items:
                    # Only process prime items
                    item_name = item.get('name', '')
                    if not item_name.endswith('Prime'):
                        continue
                    
                    # Get components (parts like Blueprint, Barrel, etc.)
                    components = item.get('components', [])
                    for comp in components:
                        comp_name = comp.get('name', '')
                        ducats = comp.get('ducats')
                        
                        # Build full item name: "Lex Prime" + "Blueprint" = "Lex Prime Blueprint"
                        if comp_name and ducats is not None:
                            full_comp_name = f"{item_name} {comp_name}"
                            ducat_items[full_comp_name] = ducats
                            
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Warning: Failed to fetch {category}: {e}")
                continue
        
        # Save to database
        with self._lock:
            cursor = self.conn.cursor()
            
            # Clear existing ducat data
            cursor.execute('DELETE FROM item_ducats')
            
            now = datetime.now().isoformat()
            for item_name, ducats in ducat_items.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO item_ducats (item_name, ducats, last_updated)
                    VALUES (?, ?, ?)
                ''', (item_name, ducats, now))
            
            self.conn.commit()
        
        if progress_callback:
            progress_callback(f"Synced {len(ducat_items)} ducat values")
        
        return len(ducat_items)
    
    def get_all_rare_items(self) -> list[RareItem]:
        """Get all rare items with their source relics."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT item_name, relic_era, relic_name, relic_full, is_vaulted
            FROM rare_items
            ORDER BY item_name
        ''')
        
        return [
            RareItem(
                item_name=row['item_name'],
                relic_era=row['relic_era'],
                relic_name=row['relic_name'],
                relic_full=row['relic_full'],
                is_vaulted=bool(row['is_vaulted'])
            )
            for row in cursor.fetchall()
        ]
    
    def get_relics_for_item(self, item_name: str) -> list[RareItem]:
        """Find which relics drop a specific rare item."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT item_name, relic_era, relic_name, relic_full, is_vaulted
            FROM rare_items
            WHERE item_name LIKE ?
            ORDER BY relic_era, relic_name
        ''', (f'%{item_name}%',))
        
        return [
            RareItem(
                item_name=row['item_name'],
                relic_era=row['relic_era'],
                relic_name=row['relic_name'],
                relic_full=row['relic_full'],
                is_vaulted=bool(row['is_vaulted'])
            )
            for row in cursor.fetchall()
        ]
    
    def get_rare_from_relic(self, relic_full: str) -> Optional[str]:
        """Get the rare item from a specific relic."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT item_name FROM rare_items
            WHERE relic_full = ?
        ''', (relic_full,))
        row = cursor.fetchone()
        return row['item_name'] if row else None
    
    def search_items(self, query: str) -> list[RareItem]:
        """Search rare items by name."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT item_name, relic_era, relic_name, relic_full, is_vaulted
            FROM rare_items
            WHERE item_name LIKE ?
            ORDER BY item_name
        ''', (f'%{query}%',))
        
        return [
            RareItem(
                item_name=row['item_name'],
                relic_era=row['relic_era'],
                relic_name=row['relic_name'],
                relic_full=row['relic_full'],
                is_vaulted=bool(row['is_vaulted'])
            )
            for row in cursor.fetchall()
        ]
    
    def get_sync_info(self) -> Optional[dict]:
        """Get last sync information."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM sync_metadata WHERE id = 1')
        row = cursor.fetchone()
        if row:
            return {
                'last_sync': row['last_sync'],
                'total_relics': row['total_relics'],
                'total_rare_items': row['total_rare_items']
            }
        return None
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM relics')
        total_relics = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM rare_items')
        total_rare = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT item_name) as count FROM rare_items')
        unique_items = cursor.fetchone()['count']
        
        return {
            'total_relics': total_relics,
            'total_rare_items': total_rare,
            'unique_rare_items': unique_items
        }
    
    def get_unique_rare_items(self) -> list[str]:
        """Get list of unique rare item names (no duplicates)."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT item_name FROM rare_items ORDER BY item_name')
        return [row['item_name'] for row in cursor.fetchall()]
    
    def save_item_price(self, item_name: str, url_name: str, lowest_price: int = None,
                        avg_price: float = None, volume: int = None):
        """Save or update a price for an item."""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO item_prices 
                (item_name, url_name, lowest_price, avg_price, volume, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (item_name, url_name, lowest_price, avg_price, volume, 
                  datetime.now().isoformat()))
            self.conn.commit()
    
    def get_item_price(self, item_name: str) -> Optional[dict]:
        """Get cached price for an item."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM item_prices WHERE item_name = ?
        ''', (item_name,))
        row = cursor.fetchone()
        if row:
            return {
                'item_name': row['item_name'],
                'url_name': row['url_name'],
                'lowest_price': row['lowest_price'],
                'avg_price': row['avg_price'],
                'volume': row['volume'],
                'last_updated': row['last_updated']
            }
        return None
    
    def get_all_prices(self) -> list[dict]:
        """Get all cached prices."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM item_prices ORDER BY item_name
        ''')
        return [
            {
                'item_name': row['item_name'],
                'url_name': row['url_name'],
                'lowest_price': row['lowest_price'],
                'avg_price': row['avg_price'],
                'volume': row['volume'],
                'last_updated': row['last_updated']
            }
            for row in cursor.fetchall()
        ]
    
    def get_all_relic_items(self) -> list[dict]:
        """Get all unique item+rarity combinations from relics.
        
        Note: WFCD data has incorrect rarity labels - items with ~25% drop chance
        are labeled as 'Uncommon' when they should be 'Common'. We fix this by
        determining rarity from the drop chance instead:
        - ~2% = Rare (100 ducats)
        - ~11% = Uncommon (45 ducats)
        - ~25% = Common (15 ducats)
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT item_name, rarity, chance_intact
            FROM relic_rewards
            ORDER BY item_name, rarity
        ''')
        
        results = []
        for row in cursor.fetchall():
            item_name = row['item_name']
            chance = row['chance_intact'] or 0
            
            # Determine correct rarity from drop chance
            if chance <= 5:  # ~2%
                correct_rarity = "Rare"
            elif chance <= 15:  # ~11%
                correct_rarity = "Uncommon"
            else:  # ~25.33%
                correct_rarity = "Common"
            
            results.append({
                'item_name': item_name,
                'rarity': correct_rarity
            })
        
        return results
    
    def get_prices_for_rare_items(self) -> list[dict]:
        """Get prices joined with rare items info."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT 
                ri.item_name,
                ip.lowest_price,
                ip.avg_price,
                ip.volume,
                ip.last_updated,
                GROUP_CONCAT(ri.relic_full, ', ') as relics
            FROM rare_items ri
            LEFT JOIN item_prices ip ON ri.item_name = ip.item_name
            GROUP BY ri.item_name
            ORDER BY ip.lowest_price DESC
        ''')
        return [
            {
                'item_name': row['item_name'],
                'lowest_price': row['lowest_price'],
                'avg_price': row['avg_price'],
                'volume': row['volume'],
                'last_updated': row['last_updated'],
                'relics': row['relics']
            }
            for row in cursor.fetchall()
        ]
    
    def get_price_stats(self) -> dict:
        """Get price database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM item_prices')
        total_priced = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT item_name) as count FROM rare_items')
        total_unique = cursor.fetchone()['count']
        
        cursor.execute('SELECT MAX(last_updated) as last FROM item_prices')
        row = cursor.fetchone()
        last_update = row['last'] if row else None
        
        return {
            'priced_items': total_priced,
            'total_unique_items': total_unique,
            'last_price_update': last_update
        }
    
    def get_item_ducats(self, item_name: str, rarity: str = None) -> int:
        """Get ducat value for an item.
        
        Args:
            item_name: The name of the item (e.g., "Lex Prime Blueprint")
            rarity: Fallback rarity to use if item not found in database
            
        Returns:
            The ducat value for the item. Falls back to rarity-based value if not found.
        """
        # Rarity-based fallback values
        RARITY_DUCATS = {
            "Common": 15,
            "Uncommon": 45,
            "Rare": 100,
            "Forma Blueprint": 0,
        }
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT ducats FROM item_ducats WHERE item_name = ?', (item_name,))
        row = cursor.fetchone()
        
        if row:
            return row['ducats']
        
        # Fallback to rarity-based value
        if rarity:
            return RARITY_DUCATS.get(rarity, 15)
        
        return 15  # Default to common value
    
    def get_all_ducats(self) -> dict[str, int]:
        """Get all item ducat values as a dictionary.
        
        Returns:
            Dictionary mapping item_name to ducat value
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT item_name, ducats FROM item_ducats')
        return {row['item_name']: row['ducats'] for row in cursor.fetchall()}
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Quick test
if __name__ == "__main__":
    db = WFCDRelicDatabase()
    
    print("Syncing from WFCD API...")
    stats = db.sync_from_wfcd(progress_callback=print)
    print(f"\nSync complete: {stats}")
    
    print("\n--- Sample Rare Items ---")
    rare = db.get_all_rare_items()[:10]
    for item in rare:
        print(f"  {item.item_name} → {item.relic_full}")
    
    print(f"\n--- Search 'Nikana' ---")
    results = db.search_items("Nikana")
    for item in results:
        print(f"  {item.item_name} → {item.relic_full}")
