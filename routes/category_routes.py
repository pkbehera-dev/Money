from flask import Blueprint, request, jsonify, redirect, url_for
from services.category_service import CategoryService

category_bp = Blueprint('category', __name__)

@category_bp.route('/api/categories')
def get_categories():
    tx_type = request.args.get('type')
    categories = CategoryService.get_all_categories(tx_type)
    return jsonify(categories)

@category_bp.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form.get('name')
    tx_type = request.form.get('type')
    if name and tx_type:
        CategoryService.add_category(name, tx_type)
    return redirect(url_for('settings.settings_page'))

@category_bp.route('/categories/delete/<int:cat_id>', methods=['POST'])
def delete_category(cat_id):
    CategoryService.delete_category(cat_id)
    return jsonify({"status": "success"})
