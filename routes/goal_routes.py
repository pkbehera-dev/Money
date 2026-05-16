from flask import Blueprint, render_template, request, redirect, url_for
from services.goal_service import GoalService

goal_bp = Blueprint('goal', __name__)

@goal_bp.route('/goals')
def goals_page():
    goals = GoalService.get_all_goals()
    return render_template('goals.html', goals=goals, partial=request.args.get('partial'))

@goal_bp.route('/goals/add', methods=['POST'])
def add_goal():
    name = request.form.get('name')
    target_amount = float(request.form.get('target_amount', 0))
    target_date = request.form.get('target_date')
    category = request.form.get('category')
    priority = request.form.get('priority', 'medium')
    notes = request.form.get('notes')
    
    GoalService.create_goal(name, target_amount, target_date, category, priority, notes)
    return redirect(url_for('goal.goals_page'))

@goal_bp.route('/goals/contribute/<int:goal_id>', methods=['POST'])
def contribute(goal_id):
    amount = float(request.form.get('amount', 0))
    GoalService.contribute_to_goal(goal_id, amount)
    return {"status": "success"}

@goal_bp.route('/goals/edit/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    if request.method == 'GET':
        goal = GoalService.get_goal_by_id(goal_id)
        return jsonify(goal) if goal else ({}, 404)
    
    name = request.form.get('name')
    target_amount = float(request.form.get('target_amount', 0))
    target_date = request.form.get('target_date')
    category = request.form.get('category')
    priority = request.form.get('priority', 'medium')
    
    GoalService.update_goal(goal_id, name, target_amount, target_date, category, priority)
    return {"status": "success"}

@goal_bp.route('/goals/delete/<int:goal_id>', methods=['POST'])
def delete_goal(goal_id):
    GoalService.delete_goal(goal_id)
    return {"status": "success"}
