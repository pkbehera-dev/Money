import sqlite3
from datetime import datetime, timedelta
from database.connection import get_db_connection, DB_PATH

class UndoService:
    DB_PATH = DB_PATH

    @classmethod
    def soft_delete(cls, table, item_id):
        """Moves an item to the trash (sets deleted_at)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Cascading notification soft deletes
        if table == 'goals':
            goal = conn.execute("SELECT name FROM goals WHERE id = ?", (item_id,)).fetchone()
            if goal:
                cursor.execute("""
                    UPDATE notifications 
                    SET deleted_at = ? 
                    WHERE type = 'goal' AND message LIKE ? AND deleted_at IS NULL
                """, (now, f"%{goal['name']}%"))
        elif table == 'subscriptions':
            sub = conn.execute("SELECT name FROM subscriptions WHERE id = ?", (item_id,)).fetchone()
            if sub:
                cursor.execute("""
                    UPDATE notifications 
                    SET deleted_at = ? 
                    WHERE type = 'subscription' AND message LIKE ? AND deleted_at IS NULL
                """, (now, f"%{sub['name']}%"))
                
        cursor.execute(f"UPDATE {table} SET deleted_at = ? WHERE id = ?", (now, item_id))
        
        conn.commit()
        conn.close()
        return True

    @classmethod
    def restore(cls, table, item_id):
        """Restores a soft-deleted item"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE {table} SET deleted_at = NULL WHERE id = ?", (item_id,))
        
        conn.commit()
        conn.close()
        return True

    @classmethod
    def permanent_delete_cron(cls):
        """
        Background task to permanently delete items older than 30 days.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Items deleted more than 30 days ago
        threshold = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        tables = ['transactions', 'budgets', 'goals', 'subscriptions', 'assets', 'loans', 'people_ledger', 'accounts', 'credit_cards', 'notifications']
        for table in tables:
            # Handle cascading deletes for database integrity
            if table == 'loans':
                cursor.execute(f"DELETE FROM loan_payments WHERE loan_id IN (SELECT id FROM loans WHERE deleted_at < ?)", (threshold,))
            elif table == 'people_ledger':
                cursor.execute(f"DELETE FROM transactions WHERE person_id IN (SELECT id FROM people_ledger WHERE deleted_at < ?)", (threshold,))
                
            cursor.execute(f"DELETE FROM {table} WHERE deleted_at < ?", (threshold,))
            
        conn.commit()
        conn.close()

    @classmethod
    def permanent_delete(cls, table, item_id):
        """Permanently deletes an item from the database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Cascading deletes
        if table == 'loans':
            cursor.execute("DELETE FROM loan_payments WHERE loan_id = ?", (item_id,))
        elif table == 'transactions':
            cursor.execute("DELETE FROM loan_payments WHERE transaction_id = ?", (item_id,))
        elif table == 'people_ledger':
            cursor.execute("DELETE FROM transactions WHERE person_id = ?", (item_id,))
        elif table == 'budgets':
            budget = conn.execute("SELECT name FROM budgets WHERE id = ?", (item_id,)).fetchone()
            if budget:
                cursor.execute("DELETE FROM notifications WHERE type = 'budget' AND (title = ? OR message LIKE ?)", (f"Budget Alert: {budget['name']}", f"%{budget['name']}%"))
        elif table == 'goals':
            goal = conn.execute("SELECT name FROM goals WHERE id = ?", (item_id,)).fetchone()
            if goal:
                cursor.execute("DELETE FROM notifications WHERE type = 'goal' AND message LIKE ?", (f"%{goal['name']}%",))
        elif table == 'subscriptions':
            sub = conn.execute("SELECT name FROM subscriptions WHERE id = ?", (item_id,)).fetchone()
            if sub:
                cursor.execute("DELETE FROM notifications WHERE type = 'subscription' AND message LIKE ?", (f"%{sub['name']}%",))
            
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        
        conn.commit()
        conn.close()
        return True

    @classmethod
    def get_all_deleted_items(cls, search_query=None, item_type=None):
        """Retrieves all soft-deleted items across the 9 tables with optional search and type filtering"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        deleted_items = []
        
        # Map each table to its UI type representation, search columns, and display details
        tables_meta = {
            'transactions': {
                'type': 'transaction',
                'name_col': 'notes',
                'amount_col': 'amount',
                'label': 'Transaction'
            },
            'budgets': {
                'type': 'budget',
                'name_col': 'name',
                'amount_col': 'amount',
                'label': 'Budget'
            },
            'goals': {
                'type': 'goal',
                'name_col': 'name',
                'amount_col': 'target_amount',
                'label': 'Goal'
            },
            'subscriptions': {
                'type': 'subscription',
                'name_col': 'name',
                'amount_col': 'amount',
                'label': 'Subscription'
            },
            'assets': {
                'type': 'asset',
                'name_col': 'name',
                'amount_col': 'current_value',
                'label': 'Asset'
            },
            'loans': {
                'type': 'loan',
                'name_col': 'name',
                'amount_col': 'principal',
                'label': 'Loan'
            },
            'people_ledger': {
                'type': 'ledger',
                'name_col': 'person_name',
                'amount_col': 'total_amount',
                'label': 'Lent/Borrow'
            },
            'accounts': {
                'type': 'account',
                'name_col': 'name',
                'amount_col': 'balance',
                'label': 'Account'
            },
            'credit_cards': {
                'type': 'card',
                'name_col': 'name',
                'amount_col': 'card_limit',
                'label': 'Credit Card'
            }
        }
        
        for table, meta in tables_meta.items():
            # Filter by type if requested
            if item_type and item_type != meta['type']:
                continue
                
            query = f"SELECT id, {meta['name_col']} as name, {meta['amount_col']} as amount, deleted_at FROM {table} WHERE deleted_at IS NOT NULL"
            
            try:
                rows = cursor.execute(query).fetchall()
            except sqlite3.OperationalError as e:
                # Fallback if table doesn't exist or column is missing
                print(f"Skipping table {table} due to error: {e}")
                continue
                
            for row in rows:
                item = dict(row)
                item['table'] = table
                item['type'] = meta['type']
                item['label'] = meta['label']
                
                # Apply search filter if provided
                if search_query:
                    sq = search_query.lower()
                    name_val = (item['name'] or '').lower()
                    label_val = item['label'].lower()
                    amount_val = str(item['amount'])
                    
                    if sq not in name_val and sq not in label_val and sq not in amount_val:
                        continue
                        
                deleted_items.append(item)
                
        conn.close()
        
        # Sort items by deleted_at descending
        deleted_items.sort(key=lambda x: x['deleted_at'] or '', reverse=True)
        return deleted_items
