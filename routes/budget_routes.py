from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from services.budget_service import BudgetService
from services.transaction_service import TransactionService
from services.account_service import AccountService

budget_bp = Blueprint('budget', __name__)

@budget_bp.route('/budgets')
def budgets_page():
    budgets = BudgetService.get_all_budgets()
    insights = BudgetService.get_budget_insights(budgets)
    categories = TransactionService.get_categories()
    accounts = AccountService.get_all_accounts()
    return render_template('budgets.html', 
                           budgets=budgets, 
                           insights=insights,
                           categories=categories,
                           accounts=accounts,
                           partial=request.args.get('partial'))

@budget_bp.route('/budgets/add', methods=['POST'])
def add_budget():
    name = request.form.get('name')
    b_type = request.form.get('type')
    target_id = request.form.get('target_id')
    amount = float(request.form.get('amount', 0))
    period = request.form.get('period')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    BudgetService.create_budget(name, b_type, target_id, amount, period, start_date, end_date)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    return redirect(url_for('budget.budgets_page'))

@budget_bp.route('/budgets/edit/<int:budget_id>', methods=['GET', 'POST'])
def edit_budget(budget_id):
    if request.method == 'GET':
        budget = BudgetService.get_budget_by_id(budget_id)
        return jsonify(budget) if budget else ({}, 404)
    
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    period = request.form.get('period')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    BudgetService.update_budget(budget_id, name, amount, period, start_date, end_date)
    return {"status": "success"}

@budget_bp.route('/budgets/delete/<int:budget_id>', methods=['POST'])
def delete_budget(budget_id):
    BudgetService.delete_budget(budget_id)
    return {"status": "success"}

@budget_bp.route('/budgets/toggle/<int:budget_id>', methods=['POST'])
def toggle_budget(budget_id):
    BudgetService.toggle_budget(budget_id)
    return {"status": "success"}
