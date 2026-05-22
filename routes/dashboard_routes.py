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
    # Force aggregate fresh stats before serving dashboard
    try:
        AnalyticsService.refresh_summaries()
    except Exception as e:
        print(f"Error refreshing summaries on dashboard load: {e}")
        
    metrics = AnalyticsService.get_quick_stats()
    
    # Safely merge card and loan reminders, and recent transactions from FinanceService
    from services.finance_service import FinanceService
    try:
        fin_metrics = FinanceService.get_dashboard_metrics()
        metrics['card_reminders'] = fin_metrics.get('card_reminders', [])
        metrics['loan_reminders'] = fin_metrics.get('loan_reminders', [])
        metrics['recent_transactions'] = fin_metrics.get('recent_transactions', [])
    except Exception as e:
        metrics['card_reminders'] = []
        metrics['loan_reminders'] = []
        metrics['recent_transactions'] = []
        print(f"Error fetching reminders for dashboard: {e}")
        
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

from flask import jsonify
import json
from database.connection import get_db_connection
from datetime import timedelta

@dashboard_bp.route('/api/dashboard/trends')
def dashboard_trends():
    range_val = request.args.get('range', '6m').lower()
    conn = get_db_connection()
    try:
        today = datetime.today().date()
        
        # 1. Determine time bounds and query targets
        if range_val == '1m':
            start_date = (today - timedelta(days=30)).isoformat()
            query = "SELECT date as label, income, expense, net_worth FROM daily_summaries WHERE date >= ? ORDER BY date ASC"
            rows = conn.execute(query, (start_date,)).fetchall()
        elif range_val == '3m':
            start_date = (today - timedelta(days=90)).isoformat()
            query = "SELECT start_date as label, income, expense, net_worth FROM weekly_summaries WHERE start_date >= ? ORDER BY start_date ASC"
            rows = conn.execute(query, (start_date,)).fetchall()
        elif range_val == '6m':
            start_date = (today - timedelta(days=180)).isoformat()
            query = "SELECT start_date as label, income, expense, net_worth FROM weekly_summaries WHERE start_date >= ? ORDER BY start_date ASC"
            rows = conn.execute(query, (start_date,)).fetchall()
        elif range_val == '1y':
            start_date = (today - timedelta(days=365)).isoformat()
            start_month = start_date[:7]
            query = "SELECT month as label, income, expense, net_worth FROM monthly_summaries WHERE month >= ? ORDER BY month ASC"
            rows = conn.execute(query, (start_month,)).fetchall()
        elif range_val == '3y':
            start_date = (today - timedelta(days=3*365)).isoformat()
            start_month = start_date[:7]
            query = "SELECT month as label, income, expense, net_worth FROM monthly_summaries WHERE month >= ? ORDER BY month ASC"
            rows = conn.execute(query, (start_month,)).fetchall()
        else: # 'all'
            query = "SELECT month as label, income, expense, net_worth FROM monthly_summaries ORDER BY month ASC"
            rows = conn.execute(query).fetchall()
            
        chart_trends = {"labels": [], "income": [], "expense": [], "net_worth": []}
        for r in rows:
            chart_trends["labels"].append(r['label'])
            chart_trends["income"].append(float(r['income'] or 0))
            chart_trends["expense"].append(float(r['expense'] or 0))
            chart_trends["net_worth"].append(float(r['net_worth'] or 0))
            
        # 2. Category Breakdown over the range
        category_totals = {}
        if range_val in ['1m', '3m', '6m']:
            start_date_val = (today - timedelta(days=30 if range_val == '1m' else (90 if range_val == '3m' else 180))).isoformat()
            cat_rows = conn.execute("SELECT category_totals FROM daily_summaries WHERE date >= ?", (start_date_val,)).fetchall()
        else:
            if range_val == '1y':
                start_month_val = (today - timedelta(days=365)).isoformat()[:7]
            elif range_val == '3y':
                start_month_val = (today - timedelta(days=3*365)).isoformat()[:7]
            else:
                start_month_val = "0000-00"
            cat_rows = conn.execute("SELECT category_totals FROM monthly_summaries WHERE month >= ?", (start_month_val,)).fetchall()
            
        for cr in cat_rows:
            if cr['category_totals']:
                try:
                    cats = json.loads(cr['category_totals'])
                    for c, v in cats.items():
                        category_totals[c] = category_totals.get(c, 0.0) + float(v)
                except Exception:
                    pass
                    
        sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        chart_category = {
            "labels": [c[0] for c in sorted_cats],
            "data": [float(c[1]) for c in sorted_cats]
        }
        
        return jsonify({
            "trends": chart_trends,
            "categories": chart_category
        })
    except Exception as e:
        print(f"Error serving dashboard API: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
