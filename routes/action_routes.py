from flask import Blueprint, request, jsonify, render_template
from services.undo_service import UndoService

action_bp = Blueprint('action', __name__)

# Centralized singular/plural to DB table mapping
TYPE_MAP = {
    'transaction': 'transactions',
    'transactions': 'transactions',
    'budget': 'budgets',
    'budgets': 'budgets',
    'goal': 'goals',
    'goals': 'goals',
    'subscription': 'subscriptions',
    'subscriptions': 'subscriptions',
    'asset': 'assets',
    'assets': 'assets',
    'loan': 'loans',
    'loans': 'loans',
    'ledger': 'people_ledger',
    'people_ledger': 'people_ledger',
    'account': 'accounts',
    'accounts': 'accounts',
    'card': 'credit_cards',
    'credit_cards': 'credit_cards',
}

@action_bp.route('/trash')
def trash_page():
    search_query = request.args.get('search', '').strip()
    item_type = request.args.get('type', '').strip()
    partial = request.args.get('partial')
    
    deleted_items = UndoService.get_all_deleted_items(search_query, item_type)
    
    # Calculate days left for each item (30 days limit)
    import datetime
    now = datetime.datetime.now()
    for item in deleted_items:
        if item['deleted_at']:
            try:
                del_time = datetime.datetime.strptime(item['deleted_at'], '%Y-%m-%d %H:%M:%S')
                days_passed = (now - del_time).days
                item['days_left'] = max(0, 30 - days_passed)
            except Exception:
                item['days_left'] = 30
        else:
            item['days_left'] = 30

    return render_template(
        'trash.html',
        deleted_items=deleted_items,
        active_filters={'search': search_query, 'type': item_type},
        partial=partial
    )

@action_bp.route('/api/actions/soft-delete', methods=['POST'])
def soft_delete():
    item_id = request.form.get('id')
    item_type = request.form.get('type')
    
    if not item_id or not item_type:
        return jsonify({"status": "error", "message": "Missing ID or Type"}), 400
        
    db_table = TYPE_MAP.get(item_type)
    if not db_table:
        return jsonify({"status": "error", "message": f"Invalid type: {item_type}"}), 400
        
    if db_table == 'transactions':
        from services.transaction_service import TransactionService
        TransactionService.delete_transaction(int(item_id))
        UndoService.soft_delete('transactions', int(item_id))
    elif db_table == 'budgets':
        from services.budget_service import BudgetService
        BudgetService.delete_budget(int(item_id))
    elif db_table == 'loans':
        from services.loan_service import LoanService
        LoanService.delete_loan(int(item_id))
    elif db_table == 'credit_cards':
        from services.credit_card_service import CreditCardService
        CreditCardService.delete_card(int(item_id))
    elif db_table == 'people_ledger':
        from services.person_service import PersonService
        PersonService.delete_person(int(item_id))
    else:
        UndoService.soft_delete(db_table, int(item_id))
        
    return jsonify({
        "status": "success", 
        "message": "Moved to Trash Bin",
        "item_id": item_id,
        "item_type": item_type
    })

@action_bp.route('/api/actions/restore', methods=['POST'])
def restore():
    item_id = request.form.get('id')
    item_type = request.form.get('type')
    
    if not item_id or not item_type:
        return jsonify({"status": "error", "message": "Missing ID or Type"}), 400
        
    db_table = TYPE_MAP.get(item_type)
    if not db_table:
        return jsonify({"status": "error", "message": f"Invalid type: {item_type}"}), 400
        
    if db_table == 'transactions':
        from services.transaction_service import TransactionService
        TransactionService.restore_transaction(int(item_id))
    elif db_table == 'people_ledger':
        UndoService.restore('people_ledger', int(item_id))
        from database.connection import get_db_connection
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        txs = conn.execute("SELECT id FROM transactions WHERE person_id = ? AND deleted_at IS NOT NULL", (item_id,)).fetchall()
        conn.close()
        for tx in txs:
            TransactionService.restore_transaction(tx['id'])
    else:
        UndoService.restore(db_table, int(item_id))
        
    # Trigger summaries update
    from services.analytics_service import AnalyticsService
    try:
        AnalyticsService.refresh_summaries()
    except Exception as e:
        print(f"Error refreshing summaries on restore: {e}")
        
    return jsonify({
        "status": "success", 
        "message": "Item restored successfully",
        "item_id": item_id,
        "item_type": item_type
    })

@action_bp.route('/api/actions/permanent-delete', methods=['POST'])
def permanent_delete():
    item_id = request.form.get('id')
    item_type = request.form.get('type')
    
    if not item_id or not item_type:
        return jsonify({"status": "error", "message": "Missing ID or Type"}), 400
        
    db_table = TYPE_MAP.get(item_type)
    if not db_table:
        return jsonify({"status": "error", "message": f"Invalid type: {item_type}"}), 400
        
    UndoService.permanent_delete(db_table, int(item_id))
    
    # Trigger summaries update
    from services.analytics_service import AnalyticsService
    try:
        AnalyticsService.refresh_summaries()
    except Exception as e:
        print(f"Error refreshing summaries on delete: {e}")
        
    return jsonify({
        "status": "success", 
        "message": "Item permanently deleted",
        "item_id": item_id,
        "item_type": item_type
    })
