import google.generativeai as genai
import sqlite3
import json
import os
from datetime import datetime, timedelta
from database.connection import DB_PATH

# Configure Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)

class GeminiService:
    @staticmethod
    def _get_cache_conn():
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_cache (
                prompt_hash TEXT PRIMARY KEY,
                response TEXT,
                timestamp DATETIME
            )
        ''')
        return conn

    @classmethod
    def ask_reasoning_minimal(cls, user_query, summary_json, mode):
        """Highly optimized Gemini call using minimal tokens."""
        prompt = f"Analyze summary: {summary_json}\nUser: {user_query}\nMode: {mode}\nReply concisely."
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Use generation_config to limit tokens further if needed
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Service Error: {str(e)}"

class LocalAIService:
    @staticmethod
    def ask_llama(user_query, context):
        """Simulated call to Llama 3.2:1B via local provider (e.g. Ollama)."""
        # In a real implementation, use requests.post('http://localhost:11434/api/generate', ...)
        return f"Local analysis: Based on your ${context.split(':')[1].split(',')[0]} balance, your spending pattern in {context.split('Spending: ')[1][:20]}... seems normal.", "Llama 3.2"
