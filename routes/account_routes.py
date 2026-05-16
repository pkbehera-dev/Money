from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from services.account_service import AccountService

account_bp = Blueprint('account', __name__)

@account_bp.route('/accounts')
def accounts_page():
    filters = {
        'type': request.args.get('type')
    }
    accounts = AccountService.get_all_accounts(filters)
    return render_template('accounts.html', accounts=accounts, active_filters=filters, partial=request.args.get('partial'))

@account_bp.route('/accounts/add', methods=['POST'])
def add_account():
    name = request.form.get('name')
    acc_type = request.form.get('type')
    balance = float(request.form.get('balance', 0.0))
    notes = request.form.get('notes')
    AccountService.create_account(name, acc_type, balance, notes)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    return redirect(url_for('account.accounts_page'))

from services.credit_card_service import CreditCardService

@account_bp.route('/api/accounts')
def get_accounts_api():
    accounts = AccountService.get_all_accounts()
    cards = CreditCardService.get_all_cards()
    
    # Merge both into a unified list
    unified = []
    for acc in accounts:
        unified.append({
            "id": acc.id,
            "name": acc.name,
            "type": acc.type,
            "balance": acc.balance
        })
    
    for card in cards:
        unified.append({
            "id": card['id'],
            "name": card['name'],
            "type": "Credit Card",
            "balance": card['card_limit'] - card['outstanding'] # Available limit
        })
        
    return jsonify(unified)
