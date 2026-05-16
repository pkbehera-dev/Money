import sqlite3
from database.connection import DB_PATH
from datetime import datetime, timedelta

class AnalyticsEngine:
    @staticmethod
    def get_db_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def generate_automated_insights(cls):
        """Generates a list of deterministic insights based on current data."""
        insights = []
        conn = cls.get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. Income vs Expense check
            this_month = datetime.now().strftime('%Y-%m')
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
                FROM transactions 
                WHERE strftime('%Y-%m', date) = ?
            ''', (this_month,))
            row = cursor.fetchone()
            if row and row['expense'] and row['income']:
                if row['expense'] > row['income']:
                    diff = row['expense'] - row['income']
                    insights.append({
                        "type": "danger",
                        "text": f"Expenses exceeded income by ₹{diff:.2f} this month.",
                        "icon": "ph-warning-circle"
                    })

            # 2. Credit Card Usage Check
            cursor.execute('SELECT name, card_limit, outstanding FROM credit_cards')
            cards = cursor.fetchall()
            for card in cards:
                if card['card_limit'] > 0:
                    usage = (card['outstanding'] / card['card_limit']) * 100
                    if usage > 80:
                        insights.append({
                            "type": "warning",
                            "text": f"Credit card '{card['name']}' is at {usage:.1f}% utilization.",
                            "icon": "ph-credit-card"
                        })

            # 3. Debt/Ledger Check
            cursor.execute('''
                SELECT person_name, SUM(total_amount - paid_amount) as balance 
                FROM people_ledger 
                WHERE type = 'lent' 
                GROUP BY person_name 
                HAVING balance > 0
            ''')
            lent_people = cursor.fetchall()
            for p in lent_people:
                insights.append({
                    "type": "info",
                    "text": f"{p['person_name']} still owes you ₹{p['balance']:.2f}.",
                    "icon": "ph-hand-coins"
                })

            # 4. Loan Due Check (within 3 days)
            three_days_later = (datetime.now() + timedelta(days=3)).day
            cursor.execute('SELECT name, total_to_pay, paid_amount, due_date FROM loans WHERE due_date <= ? AND status = "active"', (three_days_later,))
            loans = cursor.fetchall()
            for loan in loans:
                insights.append({
                    "type": "warning",
                    "text": f"Upcoming payment for {loan['name']} is due soon.",
                    "icon": "ph-calendar"
                })

        finally:
            conn.close()

        return insights

    @classmethod
    def get_summarized_context(cls):
        """Prepares a highly compressed financial summary for AI context."""
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        
        # Summary metrics
        cursor.execute("SELECT SUM(balance) FROM accounts")
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(outstanding) FROM credit_cards")
        total_debt_card = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='expense' GROUP BY category")
        categories = cursor.fetchall()
        cat_summary = ", ".join([f"{c[0]}: ₹{c[1]:.0f}" for c in categories])

        conn.close()
        
        return f"Total Balance: ₹{total_balance:.0f}, CC Debt: ₹{total_debt_card:.0f}. Spending: {cat_summary}."
