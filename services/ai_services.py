from google import genai
from google.genai import types
import sqlite3
import json
import os
from datetime import datetime, timedelta
from database.connection import DB_PATH

class GeminiService:
    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key and "YOUR_GEMINI_API_KEY" not in api_key:
                orig_google_key = os.environ.pop("GOOGLE_API_KEY", None)
                try:
                    cls._client = genai.Client(api_key=api_key)
                except Exception:
                    pass
                finally:
                    if orig_google_key:
                        os.environ["GOOGLE_API_KEY"] = orig_google_key
        return cls._client

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
        system_instruction = (
            "You are a helpful personal finance AI assistant for an Indian user. "
            "All monetary values and amounts in the provided summary JSON and user query are in Indian Rupees (₹). "
            "Always formulate your responses using the Rupee symbol '₹' (e.g., ₹10,000) and NEVER use dollars ($). "
            "Deliver highly optimized, concise, actionable, and mathematically accurate financial advice. "
            "Reason clearly about affordability, budget adherence, deficits, and savings, ensuring your tone is encouraging yet realistic."
        )
        
        prompt = f"Analyze summary: {summary_json}\nUser: {user_query}\nMode: {mode}\nReply concisely."
        
        client = cls._get_client()
        if not client:
            return "Service Error: Gemini API key is not configured."
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            return response.text
        except Exception as e:
            return f"Service Error: {str(e)}"

class LocalAIService:
    @staticmethod
    def ask_llama(user_query, context):
        """Simulated call to Llama 3.2:1B via local provider (e.g. Ollama)."""
        # In a real implementation, use requests.post('http://localhost:11434/api/generate', ...)
        return f"Local analysis: Based on your ₹{context.split(':')[1].split(',')[0]} balance, your spending pattern in {context.split('Spending: ')[1][:20]}... seems normal.", "Llama 3.2"
