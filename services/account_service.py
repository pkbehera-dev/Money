from database.connection import get_db_connection
from models.account import Account

class AccountService:
    @staticmethod
    def get_all_accounts(filters: dict = None):
        conn = get_db_connection()
        query = "SELECT * FROM accounts WHERE deleted_at IS NULL"
        params = []
        
        if filters:
            if filters.get('type'):
                query += " AND type = ?"
                params.append(filters['type'])

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [Account(**dict(row)) for row in rows]

    @staticmethod
    def get_account_by_id(account_id: int):
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
        conn.close()
        if row:
            return Account.from_row(row)
        return None

    @staticmethod
    def create_account(name: str, type: str, balance: float, notes: str = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO accounts (name, type, balance, notes) VALUES (?, ?, ?, ?)',
            (name, type, balance, notes)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    @staticmethod
    def update_balance(account_id: int, amount_change: float):
        """Update account balance. amount_change can be positive or negative."""
        conn = get_db_connection()
        conn.execute(
            'UPDATE accounts SET balance = balance + ? WHERE id = ?',
            (amount_change, account_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def delete_account(account_id: int):
        from datetime import datetime
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('UPDATE accounts SET deleted_at = ? WHERE id = ?', (now, account_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update_account(account_id: int, name: str, type: str, balance: float, notes: str):
        conn = get_db_connection()
        conn.execute(
            'UPDATE accounts SET name = ?, type = ?, balance = ?, notes = ? WHERE id = ?',
            (name, type, balance, notes, account_id)
        )
        conn.commit()
        conn.close()
