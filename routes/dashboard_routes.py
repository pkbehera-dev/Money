from flask import Blueprint, render_template, request
from datetime import datetime
from services.analytics_service import AnalyticsService
from services.goal_service import GoalService
from services.subscription_service import SubscriptionService
from services.budget_service import BudgetService
from services.asset_service import AssetService
from services.health_service import HealthService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def dashboard():
    metrics = AnalyticsService.get_quick_stats()
    insights = AnalyticsService.get_spending_insights()
    budgets = BudgetService.get_all_budgets()
    asset_stats = AssetService.get_asset_stats()
    goals = GoalService.get_all_goals()
    subscriptions = SubscriptionService.get_all_subscriptions()
    sub_stats = SubscriptionService.get_subscription_stats()
    health = HealthService.get_latest_health()
    health_history = HealthService.get_history()
    now_date = datetime.now()
    
    return render_template('dashboard.html', 
                           metrics=metrics, 
                           insights=insights,
                           budgets=budgets,
                           asset_stats=asset_stats,
                           goals=goals,
                           subscriptions=subscriptions,
                           sub_stats=sub_stats,
                           health=health,
                           health_history=health_history,
                           now=now_date,
                           partial=request.args.get('partial'))
