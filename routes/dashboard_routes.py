from flask import Blueprint, render_template, request
from services.finance_service import FinanceService
from services.account_service import AccountService
from services.analytics_engine import AnalyticsEngine
import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def dashboard():
    metrics = FinanceService.get_dashboard_metrics()
    accounts = AccountService.get_all_accounts()
    insights = AnalyticsEngine.generate_automated_insights()
    template = 'dashboard.html'
    return render_template(template, 
                           metrics=metrics, 
                           accounts=accounts, 
                           insights=insights,
                           now=datetime.datetime.now(),
                           partial=request.args.get('partial'))
