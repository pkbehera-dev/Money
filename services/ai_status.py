import requests
import os
from google import genai

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
    def get_ollama_model_name():
        """Returns the name of the first available Ollama model, or None if offline."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                if models:
                    return models[0].get('name', 'Unknown')
        except:
            pass
        return None

    @staticmethod
    def check_gemini():
        """Checks if Gemini API key is valid."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or "YOUR_GEMINI_API_KEY" in api_key:
            return False
        orig_google_key = os.environ.pop("GOOGLE_API_KEY", None)
        try:
            client = genai.Client(api_key=api_key)
            # Try listing models to verify key validity
            for _ in client.models.list():
                return True
        except:
            return False
        finally:
            if orig_google_key:
                os.environ["GOOGLE_API_KEY"] = orig_google_key
