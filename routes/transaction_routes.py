from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from services.transaction_service import TransactionService
from services.account_service import AccountService
from services.credit_card_service import CreditCardService

transaction_bp = Blueprint('transaction', __name__)

@transaction_bp.route('/transactions')
def transactions_page():
    filters = {
        'type': request.args.get('type'),
        'category': request.args.get('category'),
        'account_id': request.args.get('account_id'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'min_amount': request.args.get('min_amount'),
        'max_amount': request.args.get('max_amount'),
        'search': request.args.get('search')
    }
    sort_by = request.args.get('sort', 'date_desc')
    
    transactions = TransactionService.get_all_transactions(filters, sort_by)
    accounts = AccountService.get_all_accounts()
    cards = CreditCardService.get_all_cards()
    return render_template('transactions.html', 
                           transactions=transactions, 
                           accounts=accounts,
                           cards=cards,
                           active_filters=filters,
                           active_sort=sort_by,
                           partial=request.args.get('partial'))

@transaction_bp.route('/transactions/add', methods=['POST'])
def add_transaction():
    t_type = request.form.get('type')
    amount = float(request.form.get('amount'))
    category = 'Bank Transfer' if t_type == 'transfer' else request.form.get('category')
    date = request.form.get('date')
    # Parse Semantic IDs (A = Account, C = Card)
    raw_acc = request.form.get('account_id')
    raw_to = request.form.get('to_account_id')
    
    account_id = None
    card_id = None
    to_account_id = None
    
    if raw_acc:
        if raw_acc.startswith('A'): account_id = int(raw_acc[1:])
        elif raw_acc.startswith('C'): card_id = int(raw_acc[1:])
        else: account_id = int(raw_acc) # Fallback for old style

    if raw_to:
        if raw_to.startswith('A'): to_account_id = int(raw_to[1:])
        elif raw_to.startswith('C'): 
            # If target is a card, we treat it as the card_id for the transaction
            # (especially for transfers/bill payments)
            card_id = int(raw_to[1:])
            to_account_id = -1 # Special flag to indicate "To Card"
        else: to_account_id = int(raw_to)
    
    transfer_fee = float(request.form.get('transfer_fee', 0.0) or 0.0)

    notes = request.form.get('notes')
    tags = request.form.get('tags')
    
    # EMI Fields
    is_emi = request.form.get('is_emi') == 'on'
    emi_data = None
    if is_emi:
        emi_data = {
            'tenure': int(request.form.get('emi_tenure', 1)),
            'due_date': int(request.form.get('emi_due_date', 1)),
            'total_to_pay': float(request.form.get('emi_total_to_pay', 0) or 0)
        }
    
    TransactionService.add_transaction(
        type=t_type, 
        amount=amount, 
        category=category, 
        date=date, 
        account_id=account_id, 
        to_account_id=to_account_id, 
        notes=notes, 
        tags=tags, 
        transfer_fee=transfer_fee, 
        card_id=card_id,
        emi_data=emi_data
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success"})
    return redirect(url_for('transaction.transactions_page'))

@transaction_bp.route("/api/transactions/delete/<int:tx_id>", methods=["POST"])
def delete_transaction(tx_id):
    TransactionService.delete_transaction(tx_id)
    return {"status": "success"}

@transaction_bp.route("/api/transactions/clear-all", methods=["POST"])
def clear_all_transactions():
    TransactionService.clear_all()
    return {"status": "success"}

@transaction_bp.route('/transactions/edit/<int:tx_id>', methods=['GET', 'POST'])
def edit_transaction(tx_id):
    if request.method == 'POST':
        t_type = request.form.get('type')
        amount = float(request.form.get('amount'))
        category = 'Bank Transfer' if t_type == 'transfer' else request.form.get('category')
        date = request.form.get('date')
        
        # Parse Semantic IDs (A = Account, C = Card)
        raw_acc = request.form.get('account_id')
        raw_to = request.form.get('to_account_id')
        
        account_id = None
        card_id = None
        to_account_id = None
        
        if raw_acc:
            if raw_acc.startswith('A'): account_id = int(raw_acc[1:])
            elif raw_acc.startswith('C'): card_id = int(raw_acc[1:])
            else: account_id = int(raw_acc)

        if raw_to:
            if raw_to.startswith('A'): to_account_id = int(raw_to[1:])
            elif raw_to.startswith('C'): 
                card_id = int(raw_to[1:])
                to_account_id = -1
            else: to_account_id = int(raw_to)
            
        notes = request.form.get('notes')
        tags = request.form.get('tags')
        transfer_fee = float(request.form.get('transfer_fee', 0.0) or 0.0)
        
        TransactionService.update_transaction(
            tx_id=tx_id, 
            type=t_type, 
            amount=amount, 
            category=category, 
            date=date, 
            account_id=account_id, 
            to_account_id=to_account_id, 
            notes=notes, 
            tags=tags, 
            card_id=card_id,
            transfer_fee=transfer_fee
        )
        return jsonify({"status": "success"})
        
    tx = TransactionService.get_transaction_by_id(tx_id)
    return jsonify(tx)
