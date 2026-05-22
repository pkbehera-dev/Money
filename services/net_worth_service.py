import sqlite3
import datetime
from database.connection import get_db_connection

class NetWorthService:
    @staticmethod
    def get_db():
        return get_db_connection()

    @classmethod
    def calculate_assets(cls):
        conn = cls.get_db()
        try:
            # 1. Liquid Cash / Bank / Wallets
            accounts = conn.execute("SELECT SUM(balance) FROM accounts").fetchone()[0] or 0.0
            
            # 2. Money Lent (Remaining Balances)
            lent = conn.execute("SELECT SUM(total_amount - paid_amount) FROM people_ledger WHERE type='lent' AND deleted_at IS NULL").fetchone()[0] or 0.0
            
            # 3. Non-Liquid Assets
            non_liquid = conn.execute("SELECT SUM(current_value) FROM assets").fetchone()[0] or 0.0

            # 4. Reserved Goals
            goals = conn.execute("SELECT SUM(current_amount) FROM goals WHERE deleted_at IS NULL").fetchone()[0] or 0.0
            
            return float(accounts + lent + non_liquid + goals)
        finally:
            conn.close()

    @classmethod
    def calculate_liabilities(cls):
        conn = cls.get_db()
        try:
            # 1. Loans Remaining
            loans = conn.execute("SELECT SUM(total_to_pay - paid_amount) FROM loans WHERE status='active'").fetchone()[0] or 0.0
            
            # 2. Credit Card Outstanding (Live Transaction Logic)
            # Purchases + Withdrawals - Payments
            card_purchases = conn.execute("""
                SELECT SUM(t.amount) 
                FROM transactions t
                JOIN credit_cards c ON t.card_id = c.id
                WHERE t.card_id IS NOT NULL 
                AND t.type = 'expense' 
                AND c.status = 'active'
                AND t.deleted_at IS NULL
            """).fetchone()[0] or 0.0
            
            card_withdrawals = conn.execute("""
                SELECT SUM(t.amount) 
                FROM transactions t
                JOIN credit_cards c ON t.card_id = c.id
                WHERE t.card_id IS NOT NULL 
                AND t.type = 'transfer'
                AND t.account_id IS NULL
                AND t.to_account_id IS NOT NULL
                AND c.status = 'active'
                AND t.deleted_at IS NULL
            """).fetchone()[0] or 0.0

            card_payments = conn.execute("""
                SELECT SUM(t.amount) 
                FROM transactions t
                JOIN credit_cards c ON t.card_id = c.id
                WHERE t.card_id IS NOT NULL 
                AND t.type = 'transfer'
                AND t.account_id IS NOT NULL
                AND c.status = 'active'
                AND t.deleted_at IS NULL
            """).fetchone()[0] or 0.0
            cards = (card_purchases + card_withdrawals) - card_payments
            
            # 3. Money Borrowed (Remaining Balances)
            borrowed = conn.execute("SELECT SUM(total_amount - paid_amount) FROM people_ledger WHERE type='borrowed' AND deleted_at IS NULL").fetchone()[0] or 0.0
            
            return float(loans + cards + borrowed)
        finally:
            conn.close()

    @classmethod
    def calculate_net_worth(cls):
        assets = cls.calculate_assets()
        liabilities = cls.calculate_liabilities()
        return assets - liabilities, assets, liabilities

    @classmethod
    def update_snapshot(cls):
        """Saves a daily snapshot of net worth."""
        nw, assets, liabilities = cls.calculate_net_worth()
        today = datetime.date.today().isoformat()
        
        conn = cls.get_db()
        try:
            conn.execute('''
                INSERT OR REPLACE INTO networth_history (date, assets, liabilities, networth)
                VALUES (?, ?, ?, ?)
            ''', (today, assets, liabilities, nw))
            conn.commit()
            return True
        finally:
            conn.close()

    @classmethod
    def get_history(cls, limit=30):
        conn = cls.get_db()
        try:
            rows = conn.execute("SELECT * FROM networth_history ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()

    @classmethod
    def get_monthly_change(cls):
        """Calculates percentage change compared to start of month or last snapshot."""
        conn = cls.get_db()
        try:
            today = datetime.date.today()
            first_of_month = today.replace(day=1).isoformat()
            
            current = conn.execute("SELECT networth FROM networth_history ORDER BY date DESC LIMIT 1").fetchone()
            prev = conn.execute("SELECT networth FROM networth_history WHERE date <= ? ORDER BY date DESC LIMIT 1", (first_of_month,)).fetchone()
            
            if not current or not prev or prev[0] == 0:
                return 0.0
            
            change = ((current[0] - prev[0]) / abs(prev[0])) * 100
            return float(change)
        finally:
            conn.close()
