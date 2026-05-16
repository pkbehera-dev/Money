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
        
        # 2. Debt / Ledger Queries
        if any(word in query for word in ['who owes', 'lent', 'borrow', 'debt', 'repayment']):
            return 'debt'
        
        # 3. Affordability / Advice (Needs Reasoning)
        if any(word in query for word in ['afford', 'should i', 'buy', 'save', 'advice']):
            return 'reasoning'
        
        # 4. Patterns / Predictions
        if any(word in query for word in ['pattern', 'predict', 'trend', 'future']):
            return 'prediction'
            
        return 'general'

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
        
        summary['overview'] = {
            "liquid": float(overview['liquid'] or 0),
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
            # More comprehensive context for advice
            monthly = conn.execute("""
                SELECT 
                    SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as inc,
                    SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as exp
                FROM transactions WHERE strftime('%Y-%m', date) = ?
            """, (this_month,)).fetchone()
            summary['monthly_stats'] = {
                "income": float(monthly['inc'] or 0),
                "expenses": float(monthly['exp'] or 0)
            }
            
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
        # 1. Intent
        intent = cls.classify_intent(query)
        
        # 2. Build Summary
        summary = cls.build_summary(intent, query)
        summary_json = json.dumps(summary, separators=(',', ':'))
        
        # 3. Caching Check
        query_hash = hashlib.md5(query.encode()).hexdigest()
        summary_hash = hashlib.md5(summary_json.encode()).hexdigest()
        
        cached = cls.get_cache(query_hash, summary_hash)
        if cached:
            return cached, "Cache"

        # 4. Prompt Builder (Minimal)
        # Choose mode based on summary size
        mode = "Small"
        if len(summary_json) > 300: mode = "Medium"
        if intent in ['reasoning', 'prediction']: mode = "Large"
        
        from services.ai_services import GeminiService
        response = GeminiService.ask_reasoning_minimal(query, summary_json, mode)
        
        # 5. Save Cache
        cls.set_cache(query_hash, summary_hash, response)
        
        return response, f"Gemini ({mode})"
