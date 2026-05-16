import re
from services.analytics_engine import AnalyticsEngine
from services.ai_services import GeminiService, LocalAIService

class AIRouter:
    @staticmethod
    def classify_intent(query):
        query = query.lower()
        
        # 1. Deterministic / Logic / SQLite Lookups
        if any(word in query for word in ['spend', 'spent', 'how much', 'cost', 'expense']):
            return 'analytics'
        if any(word in query for word in ['who owes', 'lent', 'borrow', 'debt']):
            return 'lookup'
        
        # 2. Reasoning / Prediction / Advice (Gemini)
        if any(word in query for word in ['afford', 'should i', 'buy', 'save', 'advice', 'analyze']):
            return 'reasoning'
        
        # 3. Pattern / Insights (Llama)
        if any(word in query for word in ['pattern', 'unusual', 'insight', 'explain']):
            return 'insight'
            
        return 'conversational'

    @classmethod
    def get_response(cls, query):
        intent = cls.classify_intent(query)
        context = AnalyticsEngine.get_summarized_context()

        # Rule 1 & 2: Analytics / SQLite Logic (Instant)
        if intent in ['analytics', 'lookup']:
            # For demo, returning a direct analytics based summary
            # In a full app, this would trigger specific SQL generation
            return f"Logic Check: {context}", "Logic / SQL"

        # Rule 3: Local Llama
        if intent == 'insight':
            return LocalAIService.ask_llama(query, context)

        # Rule 4 & 5: Gemini Reasoning
        if intent in ['reasoning', 'conversational']:
            return GeminiService.ask_reasoning(query, context)

        return "I'm not sure how to handle that request yet.", "System"
