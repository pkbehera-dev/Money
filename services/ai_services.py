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
        import requests
        
        system_instruction = (
            "You are a helpful personal finance AI assistant. "
            "All monetary values are in Indian Rupees (₹). Use '₹' for currency. "
            "Use the provided database summary JSON context to answer the user query accurately."
        )
        
        prompt = f"System: {system_instruction}\nContext: {context}\nUser: {user_query}\nResponse:"
        
        model = "llama3.2"
        try:
            # Try to fetch available models from local Ollama
            models_resp = requests.get('http://localhost:11434/api/tags', timeout=2.0)
            if models_resp.status_code == 200:
                models_data = models_resp.json()
                if models_data.get('models'):
                    model = models_data['models'][0]['name']
        except Exception:
            pass
            
        try:
            resp = requests.post('http://localhost:11434/api/generate', json={
                'model': model,
                'prompt': prompt,
                'stream': False
            }, timeout=15.0)
            
            if resp.status_code == 200:
                res_json = resp.json()
                return res_json.get('response', ''), model
        except Exception as e:
            raise RuntimeError(f"Ollama call failed: {e}")
            
        raise RuntimeError("Ollama returned non-200 status code")
