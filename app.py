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

# Avoid dual-running initialization scripts or worker threads in Flask master process (debug mode)
is_werkzeug_parent = (os.environ.get('WERKZEUG_RUN_MAIN') is None) and (__name__ == '__main__')

if not is_werkzeug_parent:
    init_db()
    
    # Load Gemini API key from DB (for .exe users who configured it via Settings UI)
    try:
        from database.connection import get_db_connection
        _conn = get_db_connection()
        _row = _conn.execute("SELECT config_value FROM system_config WHERE config_key = 'gemini_api_key'").fetchone()
        if _row and _row['config_value']:
            db_key = _row['config_value']
            env_key = os.environ.get('GEMINI_API_KEY', '')
            # DB key takes priority, or use it if env is empty/placeholder
            if not env_key or 'YOUR_GEMINI_API_KEY' in env_key:
                os.environ['GEMINI_API_KEY'] = db_key
        _conn.close()
    except Exception:
        pass
    
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
# Register Template Filters
def days_left_filter(due_day):
    if not due_day:
        return "No due date"
    try:
        due_day = int(due_day)
    except ValueError:
        return "Invalid date"
        
    import datetime
    import calendar
    
    today = datetime.date.today()
    _, max_days = calendar.monthrange(today.year, today.month)
    target_day = min(due_day, max_days)
    
    due_date = datetime.date(today.year, today.month, target_day)
    if due_date < today:
        next_month = today.month + 1
        year = today.year
        if next_month > 12:
            next_month = 1
            year += 1
        _, next_max_days = calendar.monthrange(year, next_month)
        due_date = datetime.date(year, next_month, min(due_day, next_max_days))
        
    delta = (due_date - today).days
    
    if delta == 0:
        return "Due today"
    elif delta == 1:
        return "Due tomorrow"
    else:
        return f"Due in {delta} days"

app.jinja_env.filters['days_left'] = days_left_filter

# Context Processor for base template header config and license info
@app.context_processor
def inject_system_config():
    from database.connection import get_db_connection
    import json
    
    # 1. Fetch system configs from DB
    configs = {'user_name': 'PRADYUMNA BEHERA', 'user_nickname': 'Bapun'}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = cursor.execute("SELECT config_key, config_value FROM system_config").fetchall()
        for r in rows:
            configs[r['config_key']] = r['config_value']
        conn.close()
    except Exception:
        pass
        
    # 2. Get license days left
    days_left_str = "Pro Member"
    try:
        from run_app import get_saved_license, check_license_online
        key = get_saved_license()
        if key:
            res = check_license_online(key)
            if res.get('success') and res.get('expires_at'):
                from datetime import datetime
                expires_str = res.get('expires_at')
                try:
                    expires_dt = datetime.strptime(expires_str.split(' ')[0], "%Y-%m-%d")
                    delta = (expires_dt.date() - datetime.now().date()).days
                    if delta > 0:
                        days_left_str = f"{delta} days left"
                    else:
                        days_left_str = "License Expired"
                except Exception:
                    days_left_str = "Lifetime Member"
            elif res.get('success'):
                days_left_str = "Lifetime Member"
    except Exception:
        pass

    return {
        'system_config': configs,
        'license_days_left': days_left_str
    }


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
            
            # 4. Perform transaction archival of logs older than 12 months
            AnalyticsService.archive_old_data()
            
            print(f"Background check completed at {datetime.datetime.now()}")
            time.sleep(900) # Every 15 minutes
        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(60)

if not is_werkzeug_parent:
    worker_thread = Thread(target=run_analytics_worker, daemon=True)
    worker_thread.start()

# Background worker for soft delete permanent cleanup
def run_undo_cleanup_worker():
    print("Undo cleanup worker started.")
    from services.undo_service import UndoService
    while True:
        try:
            UndoService.permanent_delete_cron()
            time.sleep(3600)
        except Exception as e:
            print(f"Undo cleanup error: {e}")
            time.sleep(10)

if not is_werkzeug_parent:
    cleanup_thread = Thread(target=run_undo_cleanup_worker, daemon=True)
    cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='::', port=5000)
