"""
Database module for the Warframe Relic Companion.
Uses SQLite for efficient local storage of relics and inventory.
"""

import sqlite3
import os
import sys
import threading
from typing import Optional
from models import Relic, Reward, InventoryItem, RelicEra, RelicRefinement, RewardRarity


def get_app_dir() -> str:
    """Get the directory where the app/exe is located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        return os.path.dirname(sys.executable)
    else:
        # Running as Python script
        return os.path.dirname(os.path.abspath(__file__))


def get_db_dir() -> str:
    """Get the DB folder path, creating it if needed."""
    db_dir = os.path.join(get_app_dir(), "DB")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return db_dir


class RelicDatabase:
    """SQLite database for storing relics and inventory.
    
    Thread-safe implementation using connection per thread.
    """
    
    def __init__(self, db_name: str = "relic_companion.db"):
        # Store database in DB folder
        self.db_path = os.path.join(get_db_dir(), db_name)
        self._local = threading.local()
        self._lock = threading.Lock()
        # Initialize on main thread
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
        """Thread-safe connection property."""
        return self._get_conn()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Relics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                era TEXT NOT NULL,
                name TEXT NOT NULL,
                vaulted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(era, name)
            )
        ''')
        
        # Rewards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relic_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                rarity TEXT NOT NULL,
                ducats INTEGER DEFAULT 0,
                FOREIGN KEY (relic_id) REFERENCES relics(id) ON DELETE CASCADE
            )
        ''')
        
        # Inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relic_id INTEGER NOT NULL,
                refinement TEXT NOT NULL DEFAULT 'Intact',
                quantity INTEGER NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (relic_id) REFERENCES relics(id) ON DELETE CASCADE,
                UNIQUE(relic_id, refinement)
            )
        ''')
        
        # Sync metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY,
                last_sync TIMESTAMP,
                sync_source TEXT,
                total_relics INTEGER,
                total_inventory INTEGER
            )
        ''')
        
        # Profile table for AlecaFrame profile data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT,
                mastery_rank INTEGER DEFAULT 0,
                mastery_percentage REAL DEFAULT 0,
                platinum INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                endo INTEGER DEFAULT 0,
                ducats INTEGER DEFAULT 0,
                aya INTEGER DEFAULT 0,
                relics_opened INTEGER DEFAULT 0,
                trades INTEGER DEFAULT 0,
                last_sync TIMESTAMP
            )
        ''')
        
        # Run history table for Void Cascade tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                total_plat INTEGER DEFAULT 0,
                total_ducats INTEGER DEFAULT 0,
                total_items INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                silver INTEGER DEFAULT 0,
                bronze INTEGER DEFAULT 0,
                rewards_json TEXT
            )
        ''')
        
        # Create indexes for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relics_era ON relics(era)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relics_name ON relics(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rewards_relic ON rewards(relic_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_relic ON inventory(relic_id)')
        
        self.conn.commit()
    
    def close(self):
        """Close the database connection for current thread."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    # ==================== Relic Operations ====================
    
    def save_relic(self, relic: Relic) -> int:
        """Save a relic to the database. Returns the relic ID."""
        cursor = self.conn.cursor()
        
        # Insert or update relic
        cursor.execute('''
            INSERT INTO relics (era, name, vaulted, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(era, name) DO UPDATE SET
                vaulted = excluded.vaulted,
                updated_at = CURRENT_TIMESTAMP
        ''', (relic.era.value, relic.name, 1 if relic.vaulted else 0))
        
        # Get the relic ID
        cursor.execute('SELECT id FROM relics WHERE era = ? AND name = ?',
                      (relic.era.value, relic.name))
        relic_id = cursor.fetchone()['id']
        
        # Delete existing rewards and add new ones
        cursor.execute('DELETE FROM rewards WHERE relic_id = ?', (relic_id,))
        
        for reward in relic.rewards:
            cursor.execute('''
                INSERT INTO rewards (relic_id, name, rarity, ducats)
                VALUES (?, ?, ?, ?)
            ''', (relic_id, reward.name, reward.rarity.value, reward.ducats))
        
        self.conn.commit()
        return relic_id
    
    def save_relics_batch(self, relics: list[Relic]):
        """Save multiple relics efficiently in a single transaction."""
        cursor = self.conn.cursor()
        
        for relic in relics:
            # Insert or update relic
            cursor.execute('''
                INSERT INTO relics (era, name, vaulted, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(era, name) DO UPDATE SET
                    vaulted = excluded.vaulted,
                    updated_at = CURRENT_TIMESTAMP
            ''', (relic.era.value, relic.name, 1 if relic.vaulted else 0))
            
            # Get relic ID
            cursor.execute('SELECT id FROM relics WHERE era = ? AND name = ?',
                          (relic.era.value, relic.name))
            relic_id = cursor.fetchone()['id']
            
            # Delete and re-add rewards
            cursor.execute('DELETE FROM rewards WHERE relic_id = ?', (relic_id,))
            
            for reward in relic.rewards:
                cursor.execute('''
                    INSERT INTO rewards (relic_id, name, rarity, ducats)
                    VALUES (?, ?, ?, ?)
                ''', (relic_id, reward.name, reward.rarity.value, reward.ducats))
        
        self.conn.commit()
    
    def get_relic(self, era: str, name: str) -> Optional[Relic]:
        """Get a relic by era and name."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM relics WHERE era = ? AND name = ?', (era, name))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_relic(row)
    
    def get_all_relics(self) -> list[Relic]:
        """Get all relics from the database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM relics ORDER BY era, name')
        
        relics = []
        for row in cursor.fetchall():
            relics.append(self._row_to_relic(row))
        
        return relics
    
    def get_relics_by_era(self, era: str) -> list[Relic]:
        """Get all relics of a specific era."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM relics WHERE era = ? ORDER BY name', (era,))
        
        return [self._row_to_relic(row) for row in cursor.fetchall()]
    
    def _row_to_relic(self, row: sqlite3.Row) -> Relic:
        """Convert a database row to a Relic object."""
        cursor = self.conn.cursor()
        
        # Get rewards for this relic
        cursor.execute('SELECT * FROM rewards WHERE relic_id = ?', (row['id'],))
        
        rewards = []
        for reward_row in cursor.fetchall():
            rarity_map = {
                'Common': RewardRarity.COMMON,
                'Uncommon': RewardRarity.UNCOMMON,
                'Rare': RewardRarity.RARE
            }
            rewards.append(Reward(
                name=reward_row['name'],
                rarity=rarity_map.get(reward_row['rarity'], RewardRarity.COMMON),
                ducats=reward_row['ducats']
            ))
        
        era_map = {
            'Lith': RelicEra.LITH,
            'Meso': RelicEra.MESO,
            'Neo': RelicEra.NEO,
            'Axi': RelicEra.AXI
        }
        
        return Relic(
            era=era_map.get(row['era'], RelicEra.LITH),
            name=row['name'],
            rewards=rewards,
            vaulted=bool(row['vaulted'])
        )
    
    def get_relic_count(self) -> int:
        """Get total number of relics in database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM relics')
        return cursor.fetchone()['count']
    
    # ==================== Inventory Operations ====================
    
    def save_inventory_item(self, item: InventoryItem) -> int:
        """Save an inventory item. Returns the item ID."""
        cursor = self.conn.cursor()
        
        # First ensure the relic exists
        relic_id = self._get_or_create_relic_id(item.relic)
        
        # Insert or update inventory
        cursor.execute('''
            INSERT INTO inventory (relic_id, refinement, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(relic_id, refinement) DO UPDATE SET
                quantity = excluded.quantity
        ''', (relic_id, item.refinement.value, item.quantity))
        
        self.conn.commit()
        
        cursor.execute('''
            SELECT id FROM inventory 
            WHERE relic_id = ? AND refinement = ?
        ''', (relic_id, item.refinement.value))
        
        return cursor.fetchone()['id']
    
    def save_inventory_batch(self, inventory: list[InventoryItem]):
        """Save entire inventory efficiently."""
        cursor = self.conn.cursor()
        
        # Clear existing inventory
        cursor.execute('DELETE FROM inventory')
        
        for item in inventory:
            if not item.relic:
                continue
                
            relic_id = self._get_or_create_relic_id(item.relic)
            
            cursor.execute('''
                INSERT INTO inventory (relic_id, refinement, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(relic_id, refinement) DO UPDATE SET
                    quantity = excluded.quantity
            ''', (relic_id, item.refinement.value, item.quantity))
        
        self.conn.commit()
    
    def get_all_inventory(self, relics_cache: dict = None) -> list[InventoryItem]:
        """Get all inventory items."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT i.*, r.era, r.name as relic_name
            FROM inventory i
            JOIN relics r ON i.relic_id = r.id
            ORDER BY r.era, r.name, i.refinement
        ''')
        
        items = []
        for row in cursor.fetchall():
            # Get full relic object
            relic = self._row_to_relic_from_inventory(row)
            
            ref_map = {
                'Intact': RelicRefinement.INTACT,
                'Exceptional': RelicRefinement.EXCEPTIONAL,
                'Flawless': RelicRefinement.FLAWLESS,
                'Radiant': RelicRefinement.RADIANT
            }
            
            items.append(InventoryItem(
                relic=relic,
                refinement=ref_map.get(row['refinement'], RelicRefinement.INTACT),
                quantity=row['quantity']
            ))
        
        return items
    
    def _row_to_relic_from_inventory(self, row: sqlite3.Row) -> Relic:
        """Get full relic from an inventory row."""
        return self.get_relic(row['era'], row['relic_name'])
    
    def _get_or_create_relic_id(self, relic: Relic) -> int:
        """Get relic ID, creating the relic if it doesn't exist."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id FROM relics WHERE era = ? AND name = ?',
                      (relic.era.value, relic.name))
        row = cursor.fetchone()
        
        if row:
            return row['id']
        
        # Create the relic
        return self.save_relic(relic)
    
    def update_inventory_quantity(self, era: str, name: str, refinement: str, delta: int):
        """Update quantity for an inventory item."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE inventory SET quantity = quantity + ?
            WHERE relic_id = (SELECT id FROM relics WHERE era = ? AND name = ?)
            AND refinement = ?
        ''', (delta, era, name, refinement))
        
        # Remove if quantity <= 0
        cursor.execute('''
            DELETE FROM inventory WHERE quantity <= 0
        ''')
        
        self.conn.commit()
    
    def delete_inventory_item(self, era: str, name: str, refinement: str):
        """Delete an inventory item."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            DELETE FROM inventory
            WHERE relic_id = (SELECT id FROM relics WHERE era = ? AND name = ?)
            AND refinement = ?
        ''', (era, name, refinement))
        
        self.conn.commit()
    
    def get_inventory_count(self) -> tuple[int, int]:
        """Get inventory counts (unique types, total quantity)."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as types, COALESCE(SUM(quantity), 0) as total FROM inventory')
        row = cursor.fetchone()
        
        return row['types'], row['total']
    
    def clear_inventory(self):
        """Clear all inventory items."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM inventory')
        self.conn.commit()
    
    # ==================== Sync Metadata ====================
    
    def update_sync_metadata(self, source: str = "AlecaFrame"):
        """Update sync metadata."""
        cursor = self.conn.cursor()
        
        relic_count = self.get_relic_count()
        inv_types, inv_total = self.get_inventory_count()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sync_metadata (id, last_sync, sync_source, total_relics, total_inventory)
            VALUES (1, CURRENT_TIMESTAMP, ?, ?, ?)
        ''', (source, relic_count, inv_total))
        
        self.conn.commit()
    
    def get_last_sync(self) -> Optional[dict]:
        """Get last sync information."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM sync_metadata WHERE id = 1')
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'last_sync': row['last_sync'],
            'source': row['sync_source'],
            'total_relics': row['total_relics'],
            'total_inventory': row['total_inventory']
        }
    
    # ==================== Profile ====================
    
    def save_profile(self, profile_data: dict):
        """Save AlecaFrame profile data."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO profile 
            (id, username, mastery_rank, mastery_percentage, platinum, credits, endo, ducats, aya, relics_opened, trades, last_sync)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            profile_data.get('username', ''),
            profile_data.get('mastery_rank', 0),
            profile_data.get('mastery_percentage', 0),
            profile_data.get('platinum', 0),
            profile_data.get('credits', 0),
            profile_data.get('endo', 0),
            profile_data.get('ducats', 0),
            profile_data.get('aya', 0),
            profile_data.get('relics_opened', 0),
            profile_data.get('trades', 0)
        ))
        
        self.conn.commit()
    
    def get_profile(self) -> Optional[dict]:
        """Get saved profile data."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM profile WHERE id = 1')
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'username': row['username'],
            'mastery_rank': row['mastery_rank'],
            'mastery_percentage': row['mastery_percentage'],
            'platinum': row['platinum'],
            'credits': row['credits'],
            'endo': row['endo'],
            'ducats': row['ducats'],
            'aya': row['aya'],
            'relics_opened': row['relics_opened'],
            'trades': row['trades'],
            'last_sync': row['last_sync']
        }
    
    # ==================== Search ====================
    
    def search_relics(self, query: str) -> list[Relic]:
        """Search relics by name or reward name."""
        cursor = self.conn.cursor()
        
        search_term = f"%{query}%"
        
        # Search in relic names and reward names
        cursor.execute('''
            SELECT DISTINCT r.* FROM relics r
            LEFT JOIN rewards rw ON r.id = rw.relic_id
            WHERE r.name LIKE ? OR r.era LIKE ? OR rw.name LIKE ?
            ORDER BY r.era, r.name
        ''', (search_term, search_term, search_term))
        
        return [self._row_to_relic(row) for row in cursor.fetchall()]
    
    # ==================== Run History ====================
    
    def save_run(self, run_data: dict) -> int:
        """Save a run to the database. Returns the run ID."""
        import json
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO run_history (title, date, total_plat, total_ducats, total_items, gold, silver, bronze, rewards_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_data.get('title', 'Untitled Run'),
            run_data.get('date', ''),
            run_data.get('total_plat', 0),
            run_data.get('total_ducats', 0),
            run_data.get('total_items', 0),
            run_data.get('gold', 0),
            run_data.get('silver', 0),
            run_data.get('bronze', 0),
            json.dumps(run_data.get('rewards', []))
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_run_history(self, limit: int = 50) -> list[dict]:
        """Get run history, newest first."""
        import json
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM run_history ORDER BY id DESC LIMIT ?
        ''', (limit,))
        
        runs = []
        for row in cursor.fetchall():
            runs.append({
                'id': row['id'],
                'title': row['title'],
                'date': row['date'],
                'total_plat': row['total_plat'],
                'total_ducats': row['total_ducats'],
                'total_items': row['total_items'],
                'gold': row['gold'],
                'silver': row['silver'],
                'bronze': row['bronze'],
                'rewards': json.loads(row['rewards_json']) if row['rewards_json'] else []
            })
        return runs
    
    def delete_run(self, run_id: int):
        """Delete a run from history."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM run_history WHERE id = ?', (run_id,))
        self.conn.commit()
