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

@account_bp.route('/accounts/delete/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    AccountService.delete_account(account_id)
    return {"status": "success"}

@account_bp.route('/accounts/edit/<int:account_id>', methods=['GET', 'POST'])
def edit_account(account_id):
    if request.method == 'POST':
        name = request.form.get('name')
        acc_type = request.form.get('type')
        balance = float(request.form.get('balance', 0.0))
        notes = request.form.get('notes')
        AccountService.update_account(account_id, name, acc_type, balance, notes)
        return jsonify({"status": "success"})
    
    from dataclasses import asdict
    account = AccountService.get_account_by_id(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    return jsonify(asdict(account))

from services.credit_card_service import CreditCardService

@account_bp.route('/api/accounts')
def get_accounts_api():
    from dataclasses import asdict
    accounts = AccountService.get_all_accounts()
    return jsonify([asdict(acc) for acc in accounts])
