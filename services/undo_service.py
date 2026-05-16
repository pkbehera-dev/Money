import sqlite3
from datetime import datetime, timedelta
import threading

class UndoService:
    DB_PATH = 'finance.db'
    
    # In-memory store for recently deleted items (for the 30s window)
    # { 'type:id': timestamp }
    _trash_timer = {}

    @classmethod
    def soft_delete(cls, table, item_id):
        """Moves an item to the trash (sets deleted_at)"""
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(f"UPDATE {table} SET deleted_at = ? WHERE id = ?", (now, item_id))
        
        conn.commit()
        conn.close()
        
        # Track in memory for the 30s window
        key = f"{table}:{item_id}"
        cls._trash_timer[key] = datetime.now()
        return True

    @classmethod
    def restore(cls, table, item_id):
        """Restores a soft-deleted item"""
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE {table} SET deleted_at = NULL WHERE id = ?", (item_id,))
        
        conn.commit()
        conn.close()
        
        key = f"{table}:{item_id}"
        if key in cls._trash_timer:
            del cls._trash_timer[key]
        return True

    @classmethod
    def permanent_delete_cron(cls):
        """
        Background task to permanently delete items older than 30 seconds 
        (In a real app, this would be longer, but user asked for 30s undo window)
        """
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        
        # Items deleted more than 30 seconds ago
        threshold = (datetime.now() - timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        tables = ['transactions', 'budgets', 'goals', 'subscriptions', 'assets', 'loans', 'people_ledger']
        for table in tables:
            cursor.execute(f"DELETE FROM {table} WHERE deleted_at < ?", (threshold,))
            
        conn.commit()
        conn.close()

    @classmethod
    def get_recent_deletions(cls):
        return cls._trash_timer
