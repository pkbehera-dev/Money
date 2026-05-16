from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from services.subscription_service import SubscriptionService
from services.account_service import AccountService
from services.credit_card_service import CreditCardService

from services.category_service import CategoryService

subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('/subscriptions')
def subscriptions_page():
    subs = SubscriptionService.get_all_subscriptions()
    stats = SubscriptionService.get_subscription_stats()
    accounts = AccountService.get_all_accounts()
    cards = CreditCardService.get_all_cards()
    categories = CategoryService.get_all_categories()
    now_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('subscriptions.html', 
                           subscriptions=subs, 
                           stats=stats, 
                           accounts=accounts,
                           cards=cards,
                           categories=categories,
                           now_date=now_date,
                           partial=request.args.get('partial'))

@subscription_bp.route('/subscriptions/add', methods=['POST'])
def add_subscription():
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    billing_cycle = request.form.get('billing_cycle')
    next_due_date = request.form.get('next_due_date')
    category = request.form.get('category')
    payment_source = request.form.get('payment_source')
    notes = request.form.get('notes')
    
    SubscriptionService.create_subscription(name, amount, billing_cycle, next_due_date, category, payment_source, notes=notes)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"status": "success"}
    return redirect(url_for('subscription.subscriptions_page'))

@subscription_bp.route('/subscriptions/edit/<int:sub_id>', methods=['GET', 'POST'])
def edit_subscription(sub_id):
    if request.method == 'GET':
        sub = SubscriptionService.get_subscription_by_id(sub_id)
        return jsonify(sub) if sub else ({}, 404)
    
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    billing_cycle = request.form.get('billing_cycle')
    next_due_date = request.form.get('next_due_date')
    category = request.form.get('category')
    payment_source = request.form.get('payment_source')
    
    SubscriptionService.update_subscription(sub_id, name, amount, billing_cycle, next_due_date, category, payment_source)
    return {"status": "success"}

@subscription_bp.route('/subscriptions/delete/<int:sub_id>', methods=['POST'])
def delete_subscription(sub_id):
    SubscriptionService.delete_subscription(sub_id)
    return {"status": "success"}
