from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from services.goal_service import GoalService
from services.account_service import AccountService

goal_bp = Blueprint('goal', __name__)

@goal_bp.route('/goals')
def goals_page():
    goals = GoalService.get_all_goals()
    accounts = AccountService.get_all_accounts()
    return render_template('goals.html', goals=goals, accounts=accounts, partial=request.args.get('partial'))

def safe_float(val, default=0.0):
    try:
        return float(val) if val and str(val).strip() else default
    except (ValueError, TypeError):
        return default

@goal_bp.route('/goals/add', methods=['POST'])
def add_goal():
    name = request.form.get('name')
    target_amount = safe_float(request.form.get('target_amount'))
    target_date = request.form.get('target_date')
    category = request.form.get('category')
    priority = request.form.get('priority', 'medium')
    notes = request.form.get('notes')
    
    GoalService.create_goal(name, target_amount, target_date, category, priority, notes)
    return redirect(url_for('goal.goals_page'))

@goal_bp.route('/goals/contribute/<int:goal_id>', methods=['POST'])
def contribute(goal_id):
    try:
        amount = safe_float(request.form.get('amount'))
        account_id = request.form.get('account_id')
        account_id = int(account_id) if account_id and account_id.strip() else None
        GoalService.contribute_to_goal(goal_id, amount, account_id)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@goal_bp.route('/goals/withdraw/<int:goal_id>', methods=['POST'])
def withdraw(goal_id):
    try:
        amount = safe_float(request.form.get('amount'))
        account_id = request.form.get('account_id')
        account_id = int(account_id) if account_id and account_id.strip() else None
        success, msg = GoalService.withdraw_from_goal(goal_id, amount, account_id)
        if success:
            return {"status": "success"}
        return {"status": "error", "message": msg}, 400
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@goal_bp.route('/goals/edit/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    if request.method == 'GET':
        goal = GoalService.get_goal_by_id(goal_id)
        return jsonify(goal) if goal else ({}, 404)
    
    name = request.form.get('name')
    target_amount = safe_float(request.form.get('target_amount'))
    target_date = request.form.get('target_date')
    category = request.form.get('category')
    priority = request.form.get('priority', 'medium')
    
    GoalService.update_goal(
        goal_id,
        name=name,
        target_amount=target_amount,
        target_date=target_date,
        category=category,
        priority=priority
    )
    return {"status": "success"}

@goal_bp.route('/goals/delete/<int:goal_id>', methods=['POST'])
def delete_goal(goal_id):
    GoalService.delete_goal(goal_id)
    return {"status": "success"}
