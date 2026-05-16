from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from services.person_service import PersonService
from services.account_service import AccountService

person_bp = Blueprint('person', __name__)

@person_bp.route('/ledger')
def ledger_page():
    filters = {
        'type': request.args.get('type'),
        'status': request.args.get('status')
    }
    people = PersonService.get_all_people(filters)
    accounts = AccountService.get_all_accounts()
    return render_template('ledger.html', 
                           people=people, 
                           accounts=accounts,
                           active_filters=filters, 
                           partial=request.args.get('partial'))

@person_bp.route('/ledger/add', methods=['POST'])
def add_person():
    name = request.form.get('name')
    l_type = request.form.get('type')
    notes = request.form.get('notes')
    date = request.form.get('date')
    account_id = request.form.get('account_id')
    
    PersonService.add_person(name, l_type, amount, notes, date, account_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    return redirect(url_for('person.ledger_page'))

@person_bp.route('/ledger/pay/<int:person_id>', methods=['POST'])
def pay_person(person_id):
    amount = float(request.form.get('amount'))
    account_id = request.form.get('account_id')
    PersonService.record_payment(person_id, amount, account_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    return redirect(url_for('person.ledger_page'))

@person_bp.route("/ledger/settle/<int:person_id>", methods=["POST"])
def settle_person(person_id):
    account_id = request.form.get("account_id")
    if account_id: account_id = int(account_id)
    PersonService.settle_person(person_id, account_id)
    return {"status": "success"}

