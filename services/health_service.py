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
        this_month = datetime.now().strftime('%Y-%m')
        
        # 1. Liquid Cash (excluding deleted accounts)
        liquid_cash = conn.execute("SELECT SUM(balance) FROM accounts WHERE deleted_at IS NULL").fetchone()[0] or 0.0
        
        # 2. Dynamic Credit Card Outstanding and Limits
        from services.credit_card_service import CreditCardService
        cards = CreditCardService.get_all_cards()
        active_cards = [c for c in cards if c.get('status') == 'active' and not c.get('deleted_at')]
        total_limit = sum([c['card_limit'] for c in active_cards])
        credit_debt = sum([c['outstanding'] for c in active_cards])
        
        # 3. Dynamic Loan Repayments / Debt Repayments this month
        loan_repayments = conn.execute("""
            SELECT SUM(amount) 
            FROM transactions 
            WHERE category IN ('Loan Repayment', 'Debt Repayment') 
            AND date LIKE ? 
            AND deleted_at IS NULL
        """, (f"{this_month}%",)).fetchone()[0] or 0.0
        
        # 4. Loan EMIs (dynamic monthly obligation)
        loans_rows = conn.execute("""
            SELECT total_to_pay, tenure 
            FROM loans 
            WHERE status = 'active' AND deleted_at IS NULL
        """).fetchall()
        monthly_loan_emi = 0.0
        for l in loans_rows:
            tenure = l['tenure']
            if tenure > 0:
                monthly_loan_emi += (l['total_to_pay'] / tenure)
                
        conn.close()

        stats = AnalyticsService.get_quick_stats()
        
        # 1. Savings Rate (20%) - Target > 20%
        income = stats.get('income_total', 0)
        savings = stats.get('savings', 0)
        savings_rate = (savings / income * 100) if income > 0 else 0
        savings_score = min(savings_rate / 20 * 20, 20) if savings_rate > 0 else 0
        if savings_rate < 0:
            # Apply a penalty based on severity of deficit, capped at -15
            savings_score = max(-15, (savings_rate / 10) * 5)
        
        # 2. Budget Discipline (15%)
        budgets = BudgetService.get_all_budgets()
        active_budgets = [b for b in budgets if b['status'] == 'active']
        over_budget_count = len([b for b in active_budgets if b['progress'] > 100])
        budget_score = 15 - (over_budget_count * 5)
        budget_score = max(0, budget_score)
        
        # 3. Credit Usage (15%) - Target < 30%
        usage_ratio = (credit_debt / total_limit * 100) if total_limit > 0 else 0
        if total_limit == 0:
            credit_score = 15 # No credit card debt is safe
        elif usage_ratio <= 30: 
            credit_score = 15
        elif usage_ratio <= 50: 
            credit_score = 10
        elif usage_ratio <= 80: 
            credit_score = 5
        else: 
            credit_score = 0
        
        # 4. Loan Burden (15%) - Loan payment / Income < 30%
        burden_ratio = (loan_repayments / income * 100) if income > 0 else 0
        if burden_ratio == 0:
            loan_score = 15 # No loan burden is safe
        elif burden_ratio <= 30: 
            loan_score = 15
        else: 
            loan_score = max(0, 15 - (burden_ratio - 30))
        
        # 5. EMI Pressure (10%) - Checks for upcoming short-term dues vs liquid cash
        upcoming_dues = credit_debt + monthly_loan_emi
        if upcoming_dues == 0:
            emi_score = 10
        elif liquid_cash > upcoming_dues: 
            emi_score = 10
        else: 
            emi_score = 3 # High short-term pressure
        
        # 6. Goal Progress (10%)
        goals = GoalService.get_all_goals()
        active_goals = [g for g in goals if g.get('status') == 'active']
        if not active_goals:
            goal_score = 8 # Neutral/fair baseline if no goals are created
            avg_progress = 0
        else:
            avg_progress = sum([g['progress'] for g in active_goals]) / len(active_goals)
            goal_score = (avg_progress / 100 * 10)
        
        # 7. Net Worth Trend (10%) - Is it higher than last month?
        try:
            from services.net_worth_service import NetWorthService
            nw_change = NetWorthService.get_monthly_change()
            if nw_change > 2:
                net_trend_score = 10
            elif nw_change >= 0:
                net_trend_score = 6
            else:
                net_trend_score = 0 # Declining net worth
        except Exception:
            net_trend_score = 5
        
        # 8. Expense Stability (5%)
        expense_change = stats.get('expense_stats', {}).get('change_pct', 0)
        if expense_change > 15:
            expense_stability_score = 0
        elif expense_change > 0:
            expense_stability_score = 3
        else:
            expense_stability_score = 5
        
        # Final Total
        total_score = int(savings_score + budget_score + credit_score + loan_score + emi_score + goal_score + net_trend_score + expense_stability_score)
        total_score = max(0, min(100, total_score))
        
        # Determine Category
        if total_score >= 80: status = "Excellent"
        elif total_score >= 60: status = "Good"
        elif total_score >= 40: status = "Needs Attention"
        else: status = "Poor"
        
        # Reasons Engine (Always outputs detailed, context-aware factors explaining the score)
        reasons = []
        
        # Savings Rate feedback
        if income > 0:
            if savings_rate > 20:
                reasons.append(f"Savings rate is healthy ({savings_rate:.1f}%)")
            elif savings_rate > 0:
                reasons.append(f"Low savings rate ({savings_rate:.1f}%) - try to save >20%")
            else:
                reasons.append("Savings are negative (spending exceeds income)")
        else:
            reasons.append("No active monthly income recorded")
            
        # Budget discipline feedback
        if active_budgets:
            if over_budget_count > 0:
                reasons.append(f"Exceeded {over_budget_count} active budget limits")
            else:
                reasons.append("Zero budget overruns - great spending control")
        else:
            reasons.append("No budgets created to track discipline")
            
        # Credit usage feedback
        if total_limit > 0:
            if credit_debt > 0:
                if usage_ratio > 50:
                    reasons.append(f"High credit utilization ({usage_ratio:.1f}%)")
                elif usage_ratio > 30:
                    reasons.append(f"Moderate credit utilization ({usage_ratio:.1f}%)")
                else:
                    reasons.append(f"Excellent credit card utilization ({usage_ratio:.1f}%)")
            else:
                reasons.append("Zero outstanding credit card balance")
        else:
            reasons.append("No credit cards active")
            
        # Liquidity & upcoming dues feedback
        if upcoming_dues > 0:
            if liquid_cash > upcoming_dues:
                reasons.append("Good liquid cash buffer for upcoming dues")
            else:
                reasons.append("Tight liquidity vs outstanding card/loan dues")
        else:
            reasons.append("No outstanding short-term debt/EMI pressure")
            
        # Goal progress feedback
        if active_goals:
            if avg_progress >= 50:
                reasons.append(f"Excellent progress on active goals (avg: {avg_progress:.0f}%)")
            else:
                reasons.append(f"Goal progress is slow (avg: {avg_progress:.0f}%) - consider contributing")
        else:
            reasons.append("No active financial goals established")
 
        res = {
            "score": total_score,
            "status": status,
            "reasons": reasons,
            "date": datetime.now().strftime('%Y-%m-%d')
        }
        
        # Cache to DB if score changed
        HealthService.save_to_history(res)
        
        return res

    @staticmethod
    def save_to_history(data):
        conn = get_db_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        # Check if today already has an entry
        exists = conn.execute("SELECT id FROM health_history WHERE date = ?", (today,)).fetchone()
        
        if exists:
            conn.execute('''
                UPDATE health_history 
                SET score = ?, status = ?, reasons = ?
                WHERE date = ?
            ''', (data['score'], data['status'], json.dumps(data['reasons']), today))
        else:
            conn.execute('''
                INSERT INTO health_history (date, score, status, reasons)
                VALUES (?, ?, ?, ?)
            ''', (today, data['score'], data['status'], json.dumps(data['reasons'])))
        conn.commit()
        conn.close()

    @staticmethod
    def get_latest_health():
        # Always calculate the fresh score to ensure live parity, saving it to history
        fresh_health = HealthService.calculate_current_score()
        
        conn = get_db_connection()
        # Get trend (compare with previous day's snapshot)
        prev = conn.execute("SELECT score FROM health_history ORDER BY date DESC LIMIT 1 OFFSET 1").fetchone()
        trend = 0
        if prev:
            trend = fresh_health['score'] - prev['score']
            
        fresh_health['trend'] = trend
        conn.close()
        return fresh_health

    @staticmethod
    def get_history(limit=12):
        conn = get_db_connection()
        rows = conn.execute("SELECT date, score FROM health_history ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]
