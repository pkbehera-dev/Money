from flask import Blueprint, render_template, request, jsonify
from services.ai_service import AIService

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai-assistant')
def ai_assistant_page():
    return render_template('ai_assistant.html', partial=request.args.get('partial'))

@ai_bp.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    data = request.json
    query = data.get('query', '')
    
    response, source = AIService.get_ai_response(query)
    
    return jsonify({
        "response": response,
        "source": source
    })
