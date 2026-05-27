import sqlite3
import os
import sys

if getattr(sys, 'frozen', False):
    # Save database in the same directory as the runnable .exe
    DB_PATH = os.path.join(os.path.dirname(sys.executable), 'finance.db')
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finance.db')

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.close()
    
    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    
    # Ensure system_config is created and seeded for old databases too
    conn.execute("CREATE TABLE IF NOT EXISTS system_config (config_key TEXT PRIMARY KEY, config_value TEXT)")
    conn.execute("INSERT OR IGNORE INTO system_config (config_key, config_value) VALUES ('user_name', 'PRADYUMNA BEHERA'), ('user_nickname', 'Bapun')")
    
    # Seed default categories if they do not exist
    default_categories = [
        ('Salary', 'income', 'ph-bold ph-wallet', '#10b981'),
        ('Investment', 'income', 'ph-bold ph-chart-line-up', '#3b82f6'),
        ('Gift', 'income', 'ph-bold ph-gift', '#ec4899'),
        ('Freelance', 'income', 'ph-bold ph-laptop', '#8b5cf6'),
        ('Food', 'expense', 'ph-bold ph-fork-knife', '#f59e0b'),
        ('Bills', 'expense', 'ph-bold ph-receipt', '#ef4444'),
        ('Shopping', 'expense', 'ph-bold ph-shopping-bag', '#ec4899'),
        ('Entertainment', 'expense', 'ph-bold ph-popcorn', '#8b5cf6'),
        ('Travel', 'expense', 'ph-bold ph-airplane', '#06b6d4'),
        ('Health', 'expense', 'ph-bold ph-first-aid', '#10b981'),
        ('Education', 'expense', 'ph-bold ph-graduation-cap', '#6366f1'),
        ('Other', 'expense', 'ph-bold ph-dots-three-circle', '#6b7280')
    ]
    for name, cat_type, icon, color in default_categories:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, type, icon, color) VALUES (?, ?, ?, ?)",
            (name, cat_type, icon, color)
        )
        
    conn.commit()
    conn.close()


def reset_db():
    conn = get_db_connection()
    tables = [
        'accounts', 'transactions', 'recurring_transactions', 'credit_cards', 
        'loans', 'loan_payments', 'people_ledger', 'daily_summaries', 
        'weekly_summaries', 'monthly_summaries', 'yearly_summaries', 'category_summaries', 
        'transaction_archive', 'notifications', 'budgets', 'assets', 'goals', 'subscriptions', 
        'health_history', 'categories', 'networth_history', 'ai_logic_cache', 'ai_cache'
    ]
    for table in tables:
        try:
            conn.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
            
    try:
        conn.execute("DELETE FROM sqlite_sequence")
    except sqlite3.OperationalError:
        pass
            
    # Seed clean default categories
    default_categories = [
        ('Salary', 'income'),
        ('Investment', 'income'),
        ('Gift', 'income'),
        ('Freelance', 'income'),
        ('Food', 'expense'),
        ('Bills', 'expense'),
        ('Shopping', 'expense'),
        ('Entertainment', 'expense'),
        ('Travel', 'expense'),
        ('Health', 'expense'),
        ('Education', 'expense'),
        ('Other', 'expense')
    ]
    conn.executemany("INSERT INTO categories (name, type) VALUES (?, ?)", default_categories)
    conn.commit()
    conn.close()
    
    # Surgical cache refresh
    from services.analytics_service import AnalyticsService
    AnalyticsService.refresh_summaries()
