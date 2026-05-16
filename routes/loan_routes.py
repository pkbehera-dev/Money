from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from services.loan_service import LoanService
from services.account_service import AccountService

loan_bp = Blueprint('loan', __name__)

@loan_bp.route('/loans')
def loans_page():
    filters = {
        'status': request.args.get('status')
    }
    loans = LoanService.get_all_loans(filters)
    accounts = AccountService.get_all_accounts()
    from services.credit_card_service import CreditCardService
    cards = CreditCardService.get_all_cards()
    
    return render_template('loans.html', 
                           loans=loans, 
                           accounts=accounts,
                           cards=cards,
                           active_filters=filters, 
                           partial=request.args.get('partial'))

@loan_bp.route('/loans/add', methods=['POST'])
def add_loan():
    name = request.form.get('name')
    principal = float(request.form.get('principal', 0))
    total_to_pay = float(request.form.get('total_to_pay', 0))
    tenure = int(request.form.get('tenure', 0))
    due_date = int(request.form.get('due_date', 1))
    initial_paid = float(request.form.get('initial_paid', 0))
    start_date = request.form.get('start_date')
    account_id = request.form.get('account_id')
    
    LoanService.create_loan(name, principal, total_to_pay, tenure, due_date, start_date, initial_paid, account_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success"})
    return redirect(url_for('loan.loans_page'))

@loan_bp.route('/loans/payment', methods=['POST'])
def add_payment():
    loan_id = int(request.form.get('loan_id'))
    amount = float(request.form.get('amount'))
    date = request.form.get('date')
    p_type = request.form.get('type')
    notes = request.form.get('notes')
    account_id = request.form.get('account_id')
    
    LoanService.add_payment(loan_id, amount, date, p_type, notes, account_id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"status": "success"})
    return redirect(url_for('loan.loans_page'))

@loan_bp.route('/loans/delete/<int:loan_id>', methods=['POST'])
def delete_loan(loan_id):
    LoanService.delete_loan(loan_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success'})
    return redirect(url_for('loan.loans_page'))


@loan_bp.route("/loans/edit/<int:loan_id>", methods=["GET", "POST"])
def edit_loan(loan_id):
    if request.method == "POST":
        name = request.form.get("name")
        principal = float(request.form.get("principal"))
        total_to_pay = float(request.form.get("total_to_pay"))
        tenure = int(request.form.get("tenure"))
        due_date = int(request.form.get("due_date"))
        LoanService.update_loan(loan_id, name, principal, total_to_pay, tenure, due_date)
        return jsonify({"status": "success"})
    
    loan = LoanService.get_loan_by_id(loan_id)
    return jsonify(loan)


@loan_bp.route("/loans/foreclose/<int:loan_id>", methods=["POST"])
def foreclose_loan(loan_id):
    account_id = request.form.get("account_id")
    if account_id: account_id = int(account_id)
    LoanService.foreclose_loan(loan_id, account_id)
    return jsonify({"status": "success"})

