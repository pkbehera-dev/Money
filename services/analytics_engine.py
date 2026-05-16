import sqlite3
from database.connection import DB_PATH
from datetime import datetime, timedelta
from services.net_worth_service import NetWorthService

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

            # 3. Credit Card Utilization Check
            cursor.execute("SELECT * FROM credit_cards WHERE status = 'active'")
            cards = cursor.fetchall()
            for card in cards:
                # Dynamic calculation
                purchases = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id = ? AND type = 'expense' AND COALESCE(tags, '') NOT LIKE '%Silent%'", (card['id'],)).fetchone()[0] or 0
                payments = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id = ? AND type = 'transfer'", (card['id'],)).fetchone()[0] or 0
                outstanding = purchases - payments
                
                if card['card_limit'] > 0 and (outstanding / card['card_limit']) > 0.8:
                    insights.append({
                        "type": "warning",
                        "text": f"High usage on {card['name']}: {(outstanding / card['card_limit'] * 100):.1f}%",
                        "icon": "ph-credit-card"
                    })

            # 4. Debt/Ledger Check
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

            # 5. Net Worth / Debt Ratio check
            nw_total, nw_assets, nw_liabilities = NetWorthService.calculate_net_worth()
            if nw_liabilities > nw_assets:
                insights.append({
                    "type": "danger",
                    "text": f"Liabilities exceed assets by ₹{(nw_liabilities - nw_assets):.2f}. Focus on debt reduction.",
                    "icon": "ph-warning-octagon"
                })
            elif nw_liabilities > 0 and (nw_liabilities / nw_assets) > 0.8:
                 insights.append({
                    "type": "warning",
                    "text": f"High debt ratio: Liabilities are {(nw_liabilities / nw_assets * 100):.1f}% of assets.",
                    "icon": "ph-trend-down"
                })

            # 6. Budget Insights
            try:
                from services.budget_service import BudgetService
                budgets = BudgetService.get_all_budgets()
                for b in budgets:
                    if b['status'] == 'active':
                        if b['progress'] >= 100:
                            insights.append({"type": "danger", "text": f"Budget '{b['name']}' exceeded by ₹{abs(b['remaining']):.0f}!", "icon": "ph-warning"})
                        elif b['progress'] >= 85:
                            insights.append({"type": "warning", "text": f"Budget '{b['name']}' is {b['progress']:.1f}% consumed.", "icon": "ph-chart-pie-slice"})
            except: pass

            # 7. Asset Insights
            try:
                from services.asset_service import AssetService
                asset_stats = AssetService.get_asset_stats()
                if asset_stats['gain_loss'] > 0:
                    insights.append({"type": "success", "text": f"Assets grew by ₹{asset_stats['gain_loss']:.0f} (Net Worth boost!)", "icon": "ph-trend-up"})
                
                cursor.execute("SELECT name, purchase_value, current_value FROM assets WHERE current_value < purchase_value")
                for a in cursor.fetchall():
                    diff = a['purchase_value'] - a['current_value']
                    if diff > 1000:
                        insights.append({"type": "info", "text": f"Asset '{a['name']}' depreciated by ₹{diff:.0f}.", "icon": "ph-chart-line-down"})
            except: pass

            # 8. Goal Insights
            try:
                from services.goal_service import GoalService
                goals = GoalService.get_all_goals()
                for g in goals:
                    if g['status'] == 'active':
                        if g['progress'] >= 90:
                            insights.append({"type": "success", "text": f"You're almost there! '{g['name']}' is {g['progress']:.0f}% complete.", "icon": "ph-target"})
                        elif g['progress'] < 10 and g['target_date']:
                            insights.append({"type": "info", "text": f"New Goal: '{g['name']}' started. Target ₹{g['target_amount']:.0f}.", "icon": "ph-sparkle"})
            except: pass

            # 9. Subscription Insights
            try:
                from services.subscription_service import SubscriptionService
                sub_stats = SubscriptionService.get_subscription_stats()
                if sub_stats['monthly_total'] > 5000:
                    insights.append({"type": "warning", "text": f"You spend ₹{sub_stats['yearly_total']:.0f}/year on subscriptions. Consider reviewing them.", "icon": "ph-calendar-check"})
                
                upcoming = SubscriptionService.get_upcoming_renewals(days=3)
                for u in upcoming:
                    insights.append({"type": "warning", "text": f"Subscription Renewal: {u['name']} (₹{u['amount']}) is due in 3 days.", "icon": "ph-bell-ringing"})
            except: pass
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
