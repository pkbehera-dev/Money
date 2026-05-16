import requests
import os
import google.generativeai as genai

class AIStatusChecker:
    @staticmethod
    def check_llama():
        """Checks if Ollama is running on localhost."""
        try:
            # Ollama default port
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def check_gemini():
        """Checks if Gemini API key is valid."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or "YOUR_GEMINI_API_KEY" in api_key:
            return False
        try:
            genai.configure(api_key=api_key)
            # Try a very small generation or just list models
            # listing models is safer for quota
            for _ in genai.list_models():
                return True
        except:
            return False
