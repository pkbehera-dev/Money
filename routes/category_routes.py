from flask import Blueprint, request, jsonify, redirect, url_for
from services.category_service import CategoryService

category_bp = Blueprint('category', __name__)

@category_bp.route('/api/categories')
def get_categories_api():
    categories = CategoryService.get_all_categories()
    return jsonify(categories)

@category_bp.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form.get('name')
    category_type = request.form.get('type')
    if name and category_type:
        CategoryService.add_category(name, category_type)
    return redirect(url_for('settings.settings_page'))

@category_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    CategoryService.delete_category(category_id)
    return jsonify({'status': 'success'})
