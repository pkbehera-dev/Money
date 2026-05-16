import os
from flask import Flask
from threading import Thread
import time

# Initialize database and process recurring transactions
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

# Background worker for analytics and archival
def run_analytics_worker():
    while True:
        try:
            print("Running background analytics update...")
            AnalyticsService.update_summaries()
            AnalyticsService.archive_old_data()
            print("Background analytics completed.")
        except Exception as e:
            print(f"Analytics worker error: {e}")
        time.sleep(300) # Run every 5 minutes

worker_thread = Thread(target=run_analytics_worker, daemon=True)
worker_thread.start()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
