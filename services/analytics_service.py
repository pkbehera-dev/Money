import sqlite3
from database.connection import get_db_connection
from datetime import datetime, timedelta

class AnalyticsService:
    @staticmethod
    def update_summaries():
        """Aggregates raw transactions into summary tables."""
        conn = get_db_connection()
        
        # 0. Clear existing summaries to ensure non-existing months/categories are removed
        conn.execute("DELETE FROM monthly_summaries")
        conn.execute("DELETE FROM category_summaries")
        conn.execute("DELETE FROM daily_summaries")
        
        # 1. Update Monthly Summaries
        conn.execute('''
            INSERT INTO monthly_summaries (month, income_total, expense_total, savings, tx_count)
            SELECT 
                strftime('%Y-%m', date) as month,
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END),
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END) - SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),
                COUNT(*)
            FROM transactions
            WHERE category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND tags NOT LIKE '%Silent%'
            GROUP BY month
        ''')

        # 2. Update Category Summaries
        conn.execute('''
            INSERT OR REPLACE INTO category_summaries (month, category, total)
            SELECT 
                strftime('%Y-%m', date) as month,
                category,
                SUM(amount)
            FROM transactions
            WHERE type='expense' 
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND tags NOT LIKE '%Silent%'
            GROUP BY month, category
        ''')

        # 3. Update Daily Summaries (Last 30 days only to keep it fresh)
        last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        conn.execute('''
            INSERT OR REPLACE INTO daily_summaries (date, income_total, expense_total, tx_count)
            SELECT 
                date,
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END),
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),
                COUNT(*)
            FROM transactions
            WHERE date >= ? 
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND tags NOT LIKE '%Silent%'
            GROUP BY date
        ''', (last_month,))

        conn.commit()
        conn.close()

    @staticmethod
    def archive_old_data():
        """Moves transactions older than 1 year to archive."""
        conn = get_db_connection()
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Copy to archive
        conn.execute('''
            INSERT INTO transaction_archive (id, account_id, amount, type, category, date, notes, created_at)
            SELECT id, account_id, amount, type, category, date, notes, created_at
            FROM transactions
            WHERE date < ?
        ''', (one_year_ago,))
        
        # Delete from active logs
        conn.execute("DELETE FROM transactions WHERE date < ?", (one_year_ago,))
        
        conn.commit()
        conn.close()

    @staticmethod
    def get_monthly_trends():
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM monthly_summaries ORDER BY month DESC LIMIT 12").fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    @staticmethod
    def get_category_distribution(month=None):
        if not month:
            month = datetime.now().strftime('%Y-%m')
        conn = get_db_connection()
        rows = conn.execute("SELECT category, total FROM category_summaries WHERE month = ? ORDER BY total DESC", (month,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_quick_stats():
        """Returns summary cards for the current month."""
        conn = get_db_connection()
        this_month = datetime.now().strftime('%Y-%m')
        
        # We rely on the background worker to update summaries.
        # This prevents locking the DB during dashboard loads.
        
        row = conn.execute("SELECT * FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        
        # 1. LIQUID ASSETS: Sum of all Bank/Cash accounts
        liquid = conn.execute("SELECT SUM(balance) FROM accounts").fetchone()[0] or 0
        
        # 2. LOAN DEBT: Sum(TotalToPay) - Sum(AllPaymentsMade)
        # We calculate this live from the ledger
        loans_total = conn.execute("SELECT SUM(total_to_pay) FROM loans WHERE status = 'active'").fetchone()[0] or 0
        loan_payments = conn.execute("SELECT SUM(amount) FROM loan_payments").fetchone()[0] or 0
        loan_debt = loans_total - loan_payments
        
        # 3. CREDIT CARD DEBT: Sum(Purchases) - Sum(BillPayments)
        # Exclude 'Silent' transactions to avoid double counting with Loan Debt
        card_purchases = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'expense' AND tags NOT LIKE '%Silent%'").fetchone()[0] or 0
        card_payments = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'transfer'").fetchone()[0] or 0
        card_debt = card_purchases - card_payments

        # 4. NET WORTH: Liquid - (Loan Debt + Card Debt)
        net_worth = liquid - (loan_debt + card_debt)
        
        conn.close()
        
        stats = {
            "income_total": 0.0,
            "expense_total": 0.0,
            "savings": 0.0,
            "net_worth": float(net_worth),
            "loan_debt": float(loan_debt),
            "card_debt": float(card_debt)
        }
        
        if row:
            stats.update(dict(row))
            stats['net_worth'] = float(net_worth)
            
        return stats
        
    @staticmethod
    def get_behavior_analytics():
        conn = get_db_connection()
        # Weekend vs Weekday spending
        weekday_avg = conn.execute("""
            SELECT AVG(amount) FROM transactions 
            WHERE type='expense' AND strftime('%w', date) BETWEEN '1' AND '5'
        """).fetchone()[0] or 0
        weekend_avg = conn.execute("""
            SELECT AVG(amount) FROM transactions 
            WHERE type='expense' AND strftime('%w', date) IN ('0', '6')
        """).fetchone()[0] or 0
        
        # Most active day
        active_day_idx = conn.execute("""
            SELECT strftime('%w', date) as day, SUM(amount) as total 
            FROM transactions WHERE type='expense' 
            GROUP BY day ORDER BY total DESC LIMIT 1
        """).fetchone()
        
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        active_day = days[int(active_day_idx[0])] if active_day_idx else "None"
        
        diff_pct = 0
        if weekday_avg > 0:
            diff_pct = ((weekend_avg - weekday_avg) / weekday_avg) * 100

        conn.close()
        return {
            "weekend_diff": diff_pct,
            "active_day": active_day,
            "avg_daily": (weekday_avg + weekend_avg) / 2
        }

    @staticmethod
    def get_spending_insights():
        """Generates dynamic warnings and tips based on data."""
        conn = get_db_connection()
        insights = []
        
        # 1. Compare this month to last month
        this_month = datetime.now().strftime('%Y-%m')
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        m1 = conn.execute("SELECT expense_total FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        m2 = conn.execute("SELECT expense_total FROM monthly_summaries WHERE month = ?", (last_month,)).fetchone()
        
        if m1 and m2 and m2[0] > 0:
            change = ((m1[0] - m2[0]) / m2[0]) * 100
            if change > 10:
                insights.append({"type": "warning", "text": f"Spending rose {change:.1f}% compared to last month. Watch your discretionary costs."})
            elif change < -5:
                insights.append({"type": "success", "text": f"Great job! You spent {abs(change):.1f}% less than last month."})

        # 2. Category spike detection
        spikes = conn.execute("""
            SELECT category, total FROM category_summaries 
            WHERE month = ? AND total > 5000 ORDER BY total DESC LIMIT 2
        """, (this_month,)).fetchall()
        for s in spikes:
            insights.append({"type": "tip", "text": f"{s[0]} is your top expense category this month (₹{s[1]:.0f})."})

        if not insights:
            insights.append({"type": "tip", "text": "Keep recording transactions to get more detailed AI insights."})

        conn.close()
        return insights
