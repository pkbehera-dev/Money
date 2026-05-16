from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from services.credit_card_service import CreditCardService
from services.account_service import AccountService

card_bp = Blueprint('card', __name__)

@card_bp.route('/cards')
def cards_page():
    filters = {
        'usage': request.args.get('usage'),
        'outstanding': request.args.get('outstanding')
    }
    cards = CreditCardService.get_all_cards(filters)
    accounts = AccountService.get_all_accounts()
    return render_template('cards.html', 
                           cards=cards, 
                           accounts=accounts,
                           active_filters=filters, 
                           partial=request.args.get('partial'))

@card_bp.route('/cards/pay_bill', methods=['POST'])
def pay_bill():
    card_id = int(request.form.get('card_id'))
    amount = float(request.form.get('amount'))
    account_id = int(request.form.get('account_id'))
    CreditCardService.pay_bill(card_id, amount, account_id)
    return {"status": "success"}

@card_bp.route('/cards/add', methods=['POST'])
def add_card():
    name = request.form.get('name')
    limit = float(request.form.get('limit'))
    outstanding = float(request.form.get('outstanding', 0.0))
    billing_date = int(request.form.get('billing_date'))
    due_date = int(request.form.get('due_date'))
    account_id = request.form.get('account_id')
    if account_id: account_id = int(account_id)
    
    CreditCardService.add_card(name, limit, outstanding, billing_date, due_date, account_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    from flask import redirect, url_for
    return redirect(url_for('card.cards_page'))

@card_bp.route("/cards/delete/<int:card_id>", methods=["POST"])
def delete_card(card_id):
    CreditCardService.delete_card(card_id)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"status": "success"}
    return redirect(url_for("card.cards_page"))


@card_bp.route("/cards/edit/<int:card_id>", methods=["GET", "POST"])
def edit_card(card_id):
    if request.method == "POST":
        name = request.form.get("name")
        limit = float(request.form.get("limit"))
        billing_date = int(request.form.get("billing_date"))
        due_date = int(request.form.get("due_date"))
        CreditCardService.update_card(card_id, name, limit, billing_date, due_date)
        return jsonify({"status": "success"})
    
    card = CreditCardService.get_card_by_id(card_id)
    return jsonify(card)


@card_bp.route("/cards/close/<int:card_id>", methods=["POST"])
def close_card(card_id):
    amount = float(request.form.get("amount", 0))
    account_id = request.form.get("account_id")
    if account_id: account_id = int(account_id)
    
    CreditCardService.close_card(card_id, amount, account_id)
    return {"status": "success"}

