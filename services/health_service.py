import json
from datetime import datetime, timedelta
from database.connection import get_db_connection
from services.analytics_service import AnalyticsService
from services.budget_service import BudgetService
from services.goal_service import GoalService
from services.subscription_service import SubscriptionService

class HealthService:
    @staticmethod
    def calculate_current_score():
        """
        Calculates the 0-100 Financial Health Score using weighted factors.
        """
        conn = get_db_connection()
        stats = AnalyticsService.get_quick_stats()
        
        # 1. Savings Rate (20%) - Target > 20%
        income = stats.get('income_total', 0)
        savings = stats.get('savings', 0)
        savings_rate = (savings / income * 100) if income > 0 else 0
        savings_score = min(savings_rate / 20 * 20, 20) if savings_rate > 0 else 0
        if savings_rate < 0: savings_score = -5 # Penalty for spending more than earning
        
        # 2. Budget Discipline (15%)
        budgets = BudgetService.get_all_budgets()
        active_budgets = [b for b in budgets if b['status'] == 'active']
        over_budget_count = len([b for b in active_budgets if b['progress'] > 100])
        budget_score = 15 - (over_budget_count * 5)
        budget_score = max(0, budget_score)
        
        # 3. Credit Usage (15%) - Target < 30%
        # Note: We use 100,000 as a default limit if cards table is empty for simplicity
        limit_row = conn.execute("SELECT SUM(credit_limit) FROM credit_cards").fetchone()
        total_limit = limit_row[0] or 100000 
        credit_debt = stats.get('card_debt', 0)
        usage_ratio = (credit_debt / total_limit * 100) if total_limit > 0 else 0
        
        if usage_ratio <= 30: credit_score = 15
        elif usage_ratio <= 50: credit_score = 10
        elif usage_ratio <= 80: credit_score = 5
        else: credit_score = 0
        
        # 4. Loan Burden (15%) - Loan payment / Income < 30%
        loan_repayments = conn.execute("SELECT SUM(amount) FROM transactions WHERE category = 'Loan Repayment' AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')").fetchone()[0] or 0
        burden_ratio = (loan_repayments / income * 100) if income > 0 else 0
        if burden_ratio <= 30: loan_score = 15
        else: loan_score = max(0, 15 - (burden_ratio - 30))
        
        # 5. EMI Pressure (10%) - Checks for upcoming dues vs liquid cash
        upcoming_dues = stats.get('loan_debt', 0) + stats.get('card_debt', 0)
        liquid_cash = conn.execute("SELECT SUM(balance) FROM accounts").fetchone()[0] or 0
        if liquid_cash > upcoming_dues: emi_score = 10
        else: emi_score = 5 # Pressure
        
        # 6. Goal Progress (10%)
        goals = GoalService.get_all_goals()
        avg_progress = sum([g['progress'] for g in goals]) / len(goals) if goals else 0
        goal_score = (avg_progress / 100 * 10)
        
        # 7. Net Worth Trend (10%) - Is it higher than last month?
        prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        # This logic is simplified; in production we'd query the snapshot table
        net_trend_score = 10 # Assume positive for MVP
        
        # 8. Expense Stability (5%)
        expense_stability_score = 5 # Baseline
        
        # Final Total
        total_score = int(savings_score + budget_score + credit_score + loan_score + emi_score + goal_score + net_trend_score + expense_stability_score)
        total_score = max(0, min(100, total_score))
        
        # Determine Category
        if total_score >= 80: status = "Excellent"
        elif total_score >= 60: status = "Good"
        elif total_score >= 40: status = "Needs Attention"
        else: status = "Poor"
        
        # Reasons
        reasons = []
        if savings_rate > 20: reasons.append("Savings rate is healthy (>20%)")
        if over_budget_count > 0: reasons.append(f"Exceeded {over_budget_count} budget(s)")
        if usage_ratio > 50: reasons.append("High credit card utilization")
        if liquid_cash > upcoming_dues: reasons.append("Good liquidity for upcoming dues")
        
        res = {
            "score": total_score,
            "status": status,
            "reasons": reasons,
            "date": datetime.now().strftime('%Y-%m-%d')
        }
        
        # Cache to DB if score changed
        HealthService.save_to_history(res)
        
        conn.close()
        return res

    @staticmethod
    def save_to_history(data):
        conn = get_db_connection()
        # Only save if today doesn't have an entry or score is different
        today = datetime.now().strftime('%Y-%m-%d')
        last = conn.execute("SELECT score FROM health_history ORDER BY date DESC LIMIT 1").fetchone()
        
        if not last or last[0] != data['score']:
            conn.execute('''
                INSERT INTO health_history (date, score, status, reasons)
                VALUES (?, ?, ?, ?)
            ''', (today, data['score'], data['status'], json.dumps(data['reasons'])))
            conn.commit()
        conn.close()

    @staticmethod
    def get_latest_health():
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM health_history ORDER BY date DESC LIMIT 1").fetchone()
        
        if not row:
            # Recalculate if no history
            conn.close()
            return HealthService.calculate_current_score()
            
        # Get trend (compare with previous)
        prev = conn.execute("SELECT score FROM health_history ORDER BY date DESC LIMIT 1 OFFSET 1").fetchone()
        trend = 0
        if prev:
            trend = row['score'] - prev['score']
            
        res = dict(row)
        res['reasons'] = json.loads(res['reasons'])
        res['trend'] = trend
        conn.close()
        return res

    @staticmethod
    def get_history(limit=12):
        conn = get_db_connection()
        rows = conn.execute("SELECT date, score FROM health_history ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]
