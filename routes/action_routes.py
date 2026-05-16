from flask import Blueprint, request, jsonify
from services.undo_service import UndoService

action_bp = Blueprint('action', __name__)

@action_bp.route('/api/actions/soft-delete', methods=['POST'])
def soft_delete():
    item_id = request.form.get('id')
    item_type = request.form.get('type')
    
    if not item_id or not item_type:
        return jsonify({"status": "error", "message": "Missing ID or Type"}), 400
        
    if item_type == 'transactions':
        from services.transaction_service import TransactionService
        TransactionService.delete_transaction(item_id)
        # Still track for undo timer
        UndoService.soft_delete('transactions', item_id)
    elif item_type == 'budgets':
        from services.budget_service import BudgetService
        # Add delete method to budget service if missing, or use generic
        UndoService.soft_delete('budgets', item_id)
    else:
        UndoService.soft_delete(item_type, item_id)
        
    return jsonify({
        "status": "success", 
        "message": "Moved to trash",
        "item_id": item_id,
        "item_type": item_type
    })

@action_bp.route('/api/actions/restore', methods=['POST'])
def restore():
    item_id = request.form.get('id')
    item_type = request.form.get('type')
    
    if not item_id or not item_type:
        return jsonify({"status": "error", "message": "Missing ID or Type"}), 400
        
    if item_type == 'transactions':
        from services.transaction_service import TransactionService
        TransactionService.restore_transaction(item_id)
    else:
        UndoService.restore(item_type, item_id)
        
    return jsonify({
        "status": "success", 
        "message": "Item restored",
        "item_id": item_id,
        "item_type": item_type
    })
