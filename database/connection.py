import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finance.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def reset_db():
    conn = get_db_connection()
    tables = [
        'accounts', 'transactions', 'recurring_transactions', 'credit_cards', 
        'loans', 'loan_payments', 'people_ledger', 'daily_summaries', 
        'monthly_summaries', 'category_summaries', 'transaction_archive', 
        'notifications', 'budgets', 'assets', 'goals', 'subscriptions', 
        'health_history', 'categories'
    ]
    for table in tables:
        try:
            conn.execute(f"DELETE FROM {table}")
            conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
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
