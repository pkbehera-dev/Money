import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from database.connection import DB_PATH

class AIService:
    @staticmethod
    def get_db():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def classify_intent(query):
        """Step 1: Determine intent without calling AI."""
        query = query.lower()
        
        # 1. Direct Spending Queries
        if any(word in query for word in ['spend', 'spent', 'how much', 'cost', 'expense']):
            return 'spending'
        
        # 2. Salary / Income Queries
        if any(word in query for word in ['salary', 'my salary', 'income', 'paycheck', 'earning']):
            return 'salary'
        
        # 3. Debt / Ledger Queries
        if any(word in query for word in ['who owes', 'lent', 'borrow', 'debt', 'repayment']):
            return 'debt'
        # 4. Income Summary Queries (e.g., highest income previous month)
        if any(word in query for word in ['highest income', 'max income', 'most income', 'previous month income', 'income last month']):
            return 'income_summary'
        # Default fallback – treat as a reasoning/advice query
        return 'reasoning'

    @classmethod
    def build_summary(cls, intent, query):
        """Step 2 & 3: Gather required data and compress into JSON."""
        conn = cls.get_db()
        summary = {}
        
        # Basic context always included (minimal)
        this_month = datetime.now().strftime('%Y-%m')
        
        # 1. Overview
        overview = conn.execute("""
            SELECT 
                (SELECT SUM(balance) FROM accounts) as liquid,
                (SELECT SUM(outstanding) FROM credit_cards) as card_debt,
                (SELECT SUM(total_to_pay - paid_amount) FROM loans WHERE status='active') as loan_debt
        """).fetchone()
        
        summary['currency'] = 'INR'
        summary['overview'] = {
            "liquid_assets": float(overview['liquid'] or 0),
            "total_debt": float((overview['card_debt'] or 0) + (overview['loan_debt'] or 0))
        }

        # 2. Intent-specific data
        if intent == 'spending':
            # Find category if mentioned
            categories = conn.execute("SELECT DISTINCT category FROM transactions").fetchall()
            target_cat = None
            for row in categories:
                cat = row['category']
                if cat.lower() in query:
                    target_cat = cat
                    break
            
            if target_cat:
                spend = conn.execute("""
                    SELECT SUM(amount) as total FROM transactions 
                    WHERE category = ? AND strftime('%Y-%m', date) = ?
                """, (target_cat, this_month)).fetchone()
                summary['spending'] = {target_cat: float(spend['total'] or 0)}
            else:
                top_cats = conn.execute("""
                    SELECT category, SUM(amount) as total FROM transactions 
                    WHERE type='expense' AND strftime('%Y-%m', date) = ?
                    GROUP BY category ORDER BY total DESC LIMIT 3
                """, (this_month,)).fetchall()
                summary['top_spending'] = {r['category']: float(r['total']) for r in top_cats}

        elif intent == 'debt':
            lent = conn.execute("SELECT person_name, SUM(total_amount - paid_amount) as bal FROM people_ledger WHERE type='lent' GROUP BY person_name HAVING bal > 0").fetchall()
            borrowed = conn.execute("SELECT person_name, SUM(total_amount - paid_amount) as bal FROM people_ledger WHERE type='borrowed' GROUP BY person_name HAVING bal > 0").fetchall()
            summary['ledger'] = {
                "they_owe": {r['person_name']: float(r['bal']) for r in lent},
                "i_owe": {r['person_name']: float(r['bal']) for r in borrowed}
            }

        elif intent in ['reasoning', 'prediction']:
            # Current month stats (partial / month-to-date)
            monthly = conn.execute("""
                SELECT 
                    SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as inc,
                    SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as exp
                FROM transactions WHERE strftime('%Y-%m', date) = ?
            """, (this_month,)).fetchone()
            
            today_day = datetime.now().day
            summary['current_month'] = {
                "month": this_month,
                "note": f"PARTIAL data (day {today_day} of month, salary may not have arrived yet)",
                "income_so_far": float(monthly['inc'] or 0),
                "expenses_so_far": float(monthly['exp'] or 0)
            }
            
            # Last full completed month for accurate baseline
            last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            prev_monthly = conn.execute("""
                SELECT income, expense, savings FROM monthly_summaries WHERE month = ?
            """, (last_month,)).fetchone()
            if prev_monthly:
                summary['last_full_month'] = {
                    "month": last_month,
                    "income": float(prev_monthly['income'] or 0),
                    "expenses": float(prev_monthly['expense'] or 0),
                    "savings": float(prev_monthly['savings'] or 0)
                }
            
            # Average monthly stats from last 12 months for reliable baseline
            try:
                avg_row = conn.execute("""
                    SELECT AVG(income) as avg_inc, AVG(expense) as avg_exp, AVG(savings) as avg_sav
                    FROM monthly_summaries
                    WHERE month >= strftime('%Y-%m', date('now', '-12 months'))
                    AND month < ?
                """, (this_month,)).fetchone()
                if avg_row and avg_row['avg_inc']:
                    summary['avg_monthly'] = {
                        "note": "Average over last 12 completed months (reliable baseline)",
                        "avg_income": round(float(avg_row['avg_inc']), 0),
                        "avg_expenses": round(float(avg_row['avg_exp']), 0),
                        "avg_savings": round(float(avg_row['avg_sav']), 0)
                    }
            except Exception:
                pass
            
            # Enrich with precomputed multi-year comparison stats
            try:
                years_rows = conn.execute("SELECT year, income, expense, savings, net_worth, financial_score FROM yearly_summaries ORDER BY year ASC").fetchall()
                summary['yearly_history'] = [
                    {
                        "year": y["year"],
                        "income": float(y["income"] or 0),
                        "expense": float(y["expense"] or 0),
                        "savings": float(y["savings"] or 0),
                        "net_worth": float(y["net_worth"] or 0),
                        "score": int(y["financial_score"] or 80)
                    }
                    for y in years_rows
                ]
            except Exception:
                pass
            
            # Goals context
            try:
                goals = conn.execute("SELECT name, target_amount, current_amount, target_date, priority FROM goals WHERE status='active'").fetchall()
                if goals:
                    summary['active_goals'] = [
                        {"name": g['name'], "target": float(g['target_amount']), "saved": float(g['current_amount']), "deadline": g['target_date'], "priority": g['priority']}
                        for g in goals
                    ]
            except Exception:
                pass
            
        conn.close()
        return summary

    @staticmethod
    def get_cache(query_hash, summary_hash):
        conn = sqlite3.connect(DB_PATH)
        # Ensure cache table exists
        conn.execute("CREATE TABLE IF NOT EXISTS ai_logic_cache (query_hash TEXT, summary_hash TEXT, response TEXT, timestamp DATETIME, PRIMARY KEY(query_hash, summary_hash))")
        
        row = conn.execute("SELECT response, timestamp FROM ai_logic_cache WHERE query_hash = ? AND summary_hash = ?", (query_hash, summary_hash)).fetchone()
        conn.close()
        
        if row:
            ts = datetime.fromisoformat(row[1])
            if datetime.now() - ts < timedelta(hours=24):
                return row[0]
        return None

    @staticmethod
    def set_cache(query_hash, summary_hash, response):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT OR REPLACE INTO ai_logic_cache VALUES (?, ?, ?, ?)", 
                     (query_hash, summary_hash, response, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    @classmethod
    def get_ai_response(cls, query):
        # 1. Determine intent
        intent = cls.classify_intent(query)

        # 2. Salary intent – fast local answer using LocalAIService
        if intent == 'salary':
            try:
                conn_salary = sqlite3.connect(DB_PATH)
                this_month = datetime.now().strftime('%Y-%m')
                inc_row = conn_salary.execute(
                    """
                    SELECT SUM(amount) as total_income FROM transactions 
                    WHERE type='income' AND strftime('%Y-%m', date) = ?
                    """,
                    (this_month,)
                ).fetchone()
                salary_amount = float(inc_row['total_income'] or 0)
                conn_salary.close()
                from services.ai_services import LocalAIService
                context = f"Income this month: {salary_amount}"
                response, _ = LocalAIService.ask_llama(query, context)
                return response, "Local"
            except Exception:
                # Fallback to Gemini if something goes wrong
                pass

        # 3. Build summary for other intents
        summary = cls.build_summary(intent, query)
        summary_json = json.dumps(summary, separators=(',', ':'))

        # 4. Caching check
        query_hash = hashlib.md5(query.encode()).hexdigest()
        summary_hash = hashlib.md5(summary_json.encode()).hexdigest()
        cached = cls.get_cache(query_hash, summary_hash)
        if cached:
            return cached, "Cache"

        # 5. Choose response method based on intent
        if intent in ['salary', 'spending']:
            # Use the fast local model for straightforward data
            from services.ai_services import LocalAIService
            # Provide a concise textual summary to the local model
            context = json.dumps(summary, separators=(',', ':'))
            try:
                response, _ = LocalAIService.ask_llama(query, context)
            except Exception:
                # Fallback to Gemini if local model fails
                mode = "Small"
                if len(summary_json) > 300:
                    mode = "Medium"
                if intent in ['reasoning', 'prediction']:
                    mode = "Large"
                from services.ai_services import GeminiService
                response = GeminiService.ask_reasoning_minimal(query, summary_json, mode)
            cls.set_cache(query_hash, summary_hash, response)
            return response, "Local"
        elif intent == 'income_summary':
            # Calculate previous month (full month before current month)
            today = datetime.now()
            # Get the last day of previous month then format month string
            first_of_current = today.replace(day=1)
            prev_month_date = first_of_current - timedelta(days=1)
            prev_month = prev_month_date.strftime('%Y-%m')
            # Sum income for that month
            conn_local = sqlite3.connect(DB_PATH)
            inc_row = conn_local.execute(
                """
                SELECT SUM(amount) as total_income FROM transactions
                WHERE type='income' AND strftime('%Y-%m', date) = ?
                """,
                (prev_month,)
            ).fetchone()
            conn_local.close()
            # Use previously computed last_full_month income if available
            last_month_data = summary.get('last_full_month', {})
            income_amount = last_month_data.get('income')
            if income_amount is None:
                # Fallback: compute directly from DB
                conn_income = sqlite3.connect(DB_PATH)
                prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                inc_row = conn_income.execute(
                    """
                    SELECT SUM(amount) as total_income FROM transactions
                    WHERE type='income' AND strftime('%Y-%m', date) = ?
                    """,
                    (prev_month,)
                ).fetchone()
                income_amount = float(inc_row['total_income'] or 0)
                conn_income.close()
            response = f"Your total income for {last_month_data.get('month', prev_month)} was ₹{income_amount:,.2f}."
            cls.set_cache(query_hash, summary_hash, response)
            return response, "Local"
        # Fallback to Gemini for reasoning / prediction heavy queries
        mode = "Small"
        if len(summary_json) > 300:
            mode = "Medium"
        if intent in ['reasoning', 'prediction']:
            mode = "Large"
        from services.ai_services import GeminiService
        response = GeminiService.ask_reasoning_minimal(query, summary_json, mode)
        # 6. Save to cache
        cls.set_cache(query_hash, summary_hash, response)
        return response, f"Gemini ({mode})"
