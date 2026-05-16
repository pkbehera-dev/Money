import sqlite3
import json
from database.connection import get_db_connection
from datetime import datetime, timedelta

class AnalyticsService:
    @staticmethod
    def refresh_summaries():
        """Aggregates raw transactions into summary tables. Ignores soft-deleted items."""
        conn = get_db_connection()
        
        # 0. Clear existing summaries
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
            WHERE deleted_at IS NULL
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
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
            AND deleted_at IS NULL
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND tags NOT LIKE '%Silent%'
            GROUP BY month, category
        ''')

        # 3. Update Daily Summaries
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
            AND deleted_at IS NULL
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND tags NOT LIKE '%Silent%'
            GROUP BY date
        ''', (last_month,))

        conn.commit()
        conn.close()

        # 4. Trigger Checks
        try:
            from services.notification_service import NotificationService
            from services.health_service import HealthService
            NotificationService.check_all_triggers()
            HealthService.calculate_current_score()
        except Exception as e:
            print(f"Periodic check failed: {e}")

    @staticmethod
    def archive_old_data():
        """Moves transactions older than 1 year to archive."""
        conn = get_db_connection()
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        conn.execute('''
            INSERT INTO transaction_archive (id, account_id, amount, type, category, date, notes, created_at)
            SELECT id, account_id, amount, type, category, date, notes, created_at
            FROM transactions
            WHERE date < ? AND deleted_at IS NULL
        ''', (one_year_ago,))
        
        conn.execute("DELETE FROM transactions WHERE date < ? OR deleted_at IS NOT NULL", (one_year_ago,))
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
        conn = get_db_connection()
        this_month = datetime.now().strftime('%Y-%m')
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        # Monthly performance
        row = conn.execute("SELECT * FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        prev_row = conn.execute("SELECT * FROM monthly_summaries WHERE month = ?", (last_month,)).fetchone()
        
        # Account Balances (Liquid)
        liquid = conn.execute("SELECT SUM(balance) FROM accounts WHERE deleted_at IS NULL").fetchone()[0] or 0
        
        # Non-Liquid Assets (Property, Gold, etc.)
        from services.asset_service import AssetService
        non_liquid = AssetService.get_total_asset_value()
        
        # People Ledger (Lent/Borrowed)
        lent_total = conn.execute("SELECT SUM(total_amount - paid_amount) FROM people_ledger WHERE type = 'lent' AND deleted_at IS NULL").fetchone()[0] or 0
        borrowed_total = conn.execute("SELECT SUM(total_amount - paid_amount) FROM people_ledger WHERE type = 'borrowed' AND deleted_at IS NULL").fetchone()[0] or 0
        
        # Debt calculation
        loans_total = conn.execute("SELECT SUM(total_to_pay) FROM loans WHERE status = 'active' AND deleted_at IS NULL").fetchone()[0] or 0
        loan_payments = conn.execute("SELECT SUM(amount) FROM loan_payments").fetchone()[0] or 0
        loan_debt = loans_total - loan_payments
        
        card_purchases = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'expense' AND deleted_at IS NULL AND tags NOT LIKE '%Silent%'").fetchone()[0] or 0
        card_payments = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'transfer' AND deleted_at IS NULL").fetchone()[0] or 0
        card_debt = card_purchases - card_payments

        total_assets = liquid + non_liquid + lent_total
        total_liabilities = loan_debt + card_debt + borrowed_total
        net_worth = total_assets - total_liabilities
        
        # Trends
        income_this = row['income_total'] if row else 0
        income_prev = prev_row['income_total'] if prev_row else 0
        income_change = ((income_this - income_prev) / income_prev * 100) if income_prev > 0 else 0
        
        expense_this = row['expense_total'] if row else 0
        expense_prev = prev_row['expense_total'] if prev_row else 0
        expense_change = ((expense_this - expense_prev) / expense_prev * 100) if expense_prev > 0 else 0
        
        # Chart Data: Trends (6 Months)
        trend_rows = conn.execute("SELECT month, income_total, expense_total FROM monthly_summaries ORDER BY month DESC LIMIT 6").fetchall()
        trend_rows = reversed(trend_rows)
        chart_trends = {"labels": [], "income": [], "expense": []}
        for tr in trend_rows:
            chart_trends["labels"].append(tr['month'])
            chart_trends["income"].append(float(tr['income_total']))
            chart_trends["expense"].append(float(tr['expense_total']))
            
        # Chart Data: Category (This Month)
        cat_rows = conn.execute("SELECT category, total FROM category_summaries WHERE month = ? ORDER BY total DESC LIMIT 10", (this_month,)).fetchall()
        chart_category = {"labels": [], "data": []}
        for cr in cat_rows:
            chart_category["labels"].append(cr['category'])
            chart_category["data"].append(float(cr['total']))

        conn.close()
        
        return {
            "net_worth_stats": {
                "total": float(net_worth),
                "assets": float(total_assets),
                "liabilities": float(total_liabilities),
                "change_pct": income_change - expense_change
            },
            "income_stats": {
                "total": float(income_this),
                "change_pct": income_change
            },
            "expense_stats": {
                "total": float(expense_this),
                "change_pct": expense_change
            },
            "savings_stats": {
                "total": float(income_this - expense_this),
                "savings_rate": (income_this - expense_this) / income_this * 100 if income_this > 0 else 0
            },
            "net_savings": float(income_this - expense_this),
            "net_worth": float(net_worth),
            "income_total": float(income_this),
            "expense_total": float(expense_this),
            "chart_trends": chart_trends,
            "chart_category": chart_category
        }
        
    @staticmethod
    def get_behavior_analytics():
        conn = get_db_connection()
        weekday_avg = conn.execute("SELECT AVG(amount) FROM transactions WHERE type='expense' AND deleted_at IS NULL AND strftime('%w', date) BETWEEN '1' AND '5'").fetchone()[0] or 0
        weekend_avg = conn.execute("SELECT AVG(amount) FROM transactions WHERE type='expense' AND deleted_at IS NULL AND strftime('%w', date) IN ('0', '6')").fetchone()[0] or 0
        
        active_day_idx = conn.execute("SELECT strftime('%w', date) as day, SUM(amount) as total FROM transactions WHERE type='expense' AND deleted_at IS NULL GROUP BY day ORDER BY total DESC LIMIT 1").fetchone()
        
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        active_day = days[int(active_day_idx[0])] if active_day_idx and active_day_idx[0] is not None else "None"
        
        diff_pct = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0
        conn.close()
        return {"weekend_diff": diff_pct, "active_day": active_day, "avg_daily": (weekday_avg + weekend_avg) / 2}

    @staticmethod
    def get_spending_insights():
        conn = get_db_connection()
        insights = []
        this_month = datetime.now().strftime('%Y-%m')
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        m1 = conn.execute("SELECT expense_total FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        m2 = conn.execute("SELECT expense_total FROM monthly_summaries WHERE month = ?", (last_month,)).fetchone()
        
        if m1 and m2 and m2[0] > 0:
            change = ((m1[0] - m2[0]) / m2[0]) * 100
            if change > 10: insights.append({"type": "warning", "text": f"Spending rose {change:.1f}% vs last month."})
            elif change < -5: insights.append({"type": "success", "text": f"Spending down {abs(change):.1f}% vs last month."})

        spikes = conn.execute("SELECT category, total FROM category_summaries WHERE month = ? AND total > 5000 ORDER BY total DESC LIMIT 2", (this_month,)).fetchall()
        for s in spikes: insights.append({"type": "tip", "text": f"{s[0]} is a top expense (₹{s[1]:.0f})."})

        from services.budget_service import BudgetService
        budgets = BudgetService.get_all_budgets()
        for b in budgets:
            if b.status == 'active' and b.progress > 80:
                insights.append({"type": "warning" if b.progress >= 100 else "tip", "text": f"Budget '{b.name}' is {b.progress:.1f}% used."})

        if not insights: insights.append({"type": "tip", "text": "Keep tracking to get AI insights."})
        conn.close()
        return insights
