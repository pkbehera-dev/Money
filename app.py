import os
import datetime
from flask import Flask
from threading import Thread
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from database.connection import init_db
from services.recurring_service import RecurringService
from services.analytics_service import AnalyticsService

init_db()
try:
    RecurringService.process_due_transactions()
    print("Recurring transactions processed.")
except Exception as e:
    print(f"Error processing recurring transactions: {e}")

app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')
app.secret_key = 'super-secret-key-for-session'

# Import Blueprints
from routes.dashboard_routes import dashboard_bp
from routes.account_routes import account_bp
from routes.transaction_routes import transaction_bp
from routes.card_routes import card_bp
from routes.loan_routes import loan_bp
from routes.person_routes import person_bp
from routes.settings_routes import settings_bp
from routes.report_routes import report_bp
from routes.search_routes import search_bp
from routes.ai_routes import ai_bp
from routes.notification_routes import notification_bp
from routes.category_routes import category_bp
from routes.asset_routes import asset_bp
from routes.budget_routes import budget_bp
from routes.goal_routes import goal_bp
from routes.subscription_routes import subscription_bp
from routes.action_routes import action_bp

# Register Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(account_bp)
app.register_blueprint(loan_bp)
app.register_blueprint(card_bp)
app.register_blueprint(person_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(report_bp)
app.register_blueprint(search_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(category_bp)
app.register_blueprint(asset_bp)
app.register_blueprint(budget_bp)
app.register_blueprint(goal_bp)
app.register_blueprint(subscription_bp)
app.register_blueprint(action_bp)

# Background worker for analytics and archival
def run_analytics_worker():
    print("Analytics worker started.")
    while True:
        try:
            # 1. Update summaries (Transactions -> KPI tables)
            AnalyticsService.refresh_summaries()
            
            # 2. Capture Net Worth Snapshot
            from services.net_worth_service import NetWorthService
            NetWorthService.update_snapshot()
            
            # 3. Process Triggers (Budget alerts, Goal tracking, Renewals)
            from services.notification_service import NotificationService
            NotificationService.check_all_triggers()
            
            print(f"Background check completed at {datetime.now()}")
            time.sleep(900) # Every 15 minutes
        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(60)

worker_thread = Thread(target=run_analytics_worker, daemon=True)
worker_thread.start()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
