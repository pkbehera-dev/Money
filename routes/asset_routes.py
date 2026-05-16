from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from services.asset_service import AssetService
from datetime import datetime

asset_bp = Blueprint('asset', __name__)

@asset_bp.route('/assets')
def assets_page():
    assets = AssetService.get_all_assets()
    stats = AssetService.get_asset_stats()
    now_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('assets.html', assets=assets, stats=stats, now_date=now_date, partial=request.args.get('partial'))

@asset_bp.route('/assets/add', methods=['POST'])
def add_asset():
    name = request.form.get('name')
    category = request.form.get('category')
    purchase_value = float(request.form.get('purchase_value', 0))
    current_value = float(request.form.get('current_value', 0))
    purchase_date = request.form.get('purchase_date')
    notes = request.form.get('notes')
    depreciation_enabled = 1 if request.form.get('depreciation_enabled') else 0
    
    AssetService.create_asset(name, category, purchase_value, current_value, purchase_date, notes, depreciation_enabled)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    return redirect(url_for('asset.assets_page'))

@asset_bp.route('/assets/update_value/<int:asset_id>', methods=['POST'])
def update_value(asset_id):
    new_value = float(request.form.get('current_value'))
    AssetService.update_asset(asset_id, current_value=new_value)
    return {"status": "success"}

@asset_bp.route('/assets/edit/<int:asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    if request.method == 'GET':
        asset = AssetService.get_asset_by_id(asset_id)
        return jsonify(asset) if asset else ({}, 404)
    
    name = request.form.get('name')
    purchase_value = float(request.form.get('purchase_value', 0))
    current_value = float(request.form.get('current_value', 0))
    
    AssetService.update_asset(asset_id, name=name, purchase_value=purchase_value, current_value=current_value)
    return {"status": "success"}

@asset_bp.route('/assets/delete/<int:asset_id>', methods=['POST'])
def delete_asset(asset_id):
    AssetService.delete_asset(asset_id)
    return {"status": "success"}
