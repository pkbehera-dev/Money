from flask import Blueprint, request, jsonify
from services.search_service import SearchService

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search/index')
def get_search_index():
    index = SearchService.get_search_index()
    return jsonify(index)

@search_bp.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    results = SearchService.global_search(query)
    return jsonify(results)
