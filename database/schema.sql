CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    balance REAL DEFAULT 0.0,
    notes TEXT,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, -- income, expense, transfer
    amount REAL NOT NULL,
    category TEXT,
    date TEXT NOT NULL,
    account_id INTEGER,
    to_account_id INTEGER, -- For transfers
    notes TEXT,
    tags TEXT,
    recurring_id INTEGER,
    card_id INTEGER,
    person_id INTEGER,
    deleted_at DATETIME,
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(to_account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT,
    account_id INTEGER,
    to_account_id INTEGER,
    notes TEXT,
    tags TEXT,
    interval TEXT NOT NULL, -- Daily, Weekly, Monthly, Yearly, Custom
    custom_interval_days INTEGER,
    next_due_date TEXT NOT NULL,
    last_generated_date TEXT,
    is_paused INTEGER DEFAULT 0,
    deleted_at DATETIME,
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(to_account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS credit_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    card_limit REAL NOT NULL,
    outstanding REAL DEFAULT 0.0,
    billing_date INTEGER, -- day of month
    due_date INTEGER, -- day of month
    status TEXT DEFAULT 'active',
    deleted_at DATETIME,
    credit_limit REAL DEFAULT 100000
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    principal REAL NOT NULL,
    total_to_pay REAL NOT NULL, -- The absolute total including interest/fees
    paid_amount REAL DEFAULT 0.0,
    tenure INTEGER NOT NULL, -- in months
    due_date INTEGER, -- day of month
    status TEXT DEFAULT 'active', -- active, closed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    start_date DATE,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS loan_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    type TEXT NOT NULL, -- EMI, Extra, Penalty, Fee, Adjustment
    notes TEXT,
    FOREIGN KEY(loan_id) REFERENCES loans(id)
);

CREATE TABLE IF NOT EXISTS people_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_name TEXT NOT NULL,
    type TEXT NOT NULL, -- lent, borrowed
    total_amount REAL NOT NULL,
    paid_amount REAL DEFAULT 0.0,
    notes TEXT,
    status TEXT DEFAULT 'active',
    deleted_at DATETIME
);

-- Summary Tables for Performance
CREATE TABLE IF NOT EXISTS daily_summaries (
    date TEXT PRIMARY KEY, -- YYYY-MM-DD
    income REAL DEFAULT 0.0,
    expense REAL DEFAULT 0.0,
    savings REAL DEFAULT 0.0,
    net_worth REAL DEFAULT 0.0,
    financial_score INTEGER DEFAULT 0,
    credit_usage REAL DEFAULT 0.0,
    category_totals TEXT, -- JSON string
    tx_count INTEGER DEFAULT 0,
    summary_version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS weekly_summaries (
    week TEXT PRIMARY KEY, -- YYYY-Www (e.g. 2026-W20)
    start_date TEXT,
    end_date TEXT,
    income REAL DEFAULT 0.0,
    expense REAL DEFAULT 0.0,
    savings REAL DEFAULT 0.0,
    net_worth REAL DEFAULT 0.0,
    financial_score INTEGER DEFAULT 0,
    credit_usage REAL DEFAULT 0.0,
    category_totals TEXT, -- JSON string
    tx_count INTEGER DEFAULT 0,
    summary_version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS monthly_summaries (
    month TEXT PRIMARY KEY, -- YYYY-MM
    income REAL DEFAULT 0.0,
    expense REAL DEFAULT 0.0,
    savings REAL DEFAULT 0.0,
    net_worth REAL DEFAULT 0.0,
    financial_score INTEGER DEFAULT 0,
    credit_usage REAL DEFAULT 0.0,
    category_totals TEXT, -- JSON string
    tx_count INTEGER DEFAULT 0,
    summary_version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS yearly_summaries (
    year TEXT PRIMARY KEY, -- YYYY
    income REAL DEFAULT 0.0,
    expense REAL DEFAULT 0.0,
    savings REAL DEFAULT 0.0,
    net_worth REAL DEFAULT 0.0,
    financial_score INTEGER DEFAULT 0,
    credit_usage REAL DEFAULT 0.0,
    category_totals TEXT, -- JSON string
    tx_count INTEGER DEFAULT 0,
    summary_version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS category_summaries (
    month TEXT, -- YYYY-MM
    category TEXT,
    total REAL DEFAULT 0,
    PRIMARY KEY (month, category)
);

-- Archive table for raw logs older than 1 year
CREATE TABLE IF NOT EXISTS transaction_archive (
    id INTEGER PRIMARY KEY,
    account_id INTEGER,
    amount REAL,
    type TEXT,
    category TEXT,
    date TEXT,
    notes TEXT,
    created_at DATETIME
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT,
    priority TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_status INTEGER DEFAULT 0,
    action_link TEXT,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    target_id TEXT,
    amount REAL NOT NULL,
    period TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    purchase_value REAL NOT NULL,
    current_value REAL NOT NULL,
    purchase_date TEXT NOT NULL,
    depreciation_enabled INTEGER DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL DEFAULT 0.0,
    target_date TEXT,
    category TEXT,
    priority TEXT DEFAULT 'medium',
    notes TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    billing_cycle TEXT NOT NULL,
    next_due_date TEXT NOT NULL,
    category TEXT,
    payment_source TEXT,
    auto_renew INTEGER DEFAULT 1,
    notes TEXT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS health_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE DEFAULT CURRENT_DATE,
    score INTEGER,
    status TEXT,
    reasons TEXT, -- JSON string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    icon TEXT,
    deleted_at DATETIME,
    color TEXT,
    UNIQUE(name, type)
);

CREATE TABLE IF NOT EXISTS networth_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE,
    assets REAL,
    liabilities REAL,
    networth REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_logic_cache (
    query_hash TEXT,
    summary_hash TEXT,
    response TEXT,
    timestamp DATETIME,
    PRIMARY KEY(query_hash, summary_hash)
);

-- Indexes for Search and Query Optimization
CREATE INDEX IF NOT EXISTS idx_transactions_deleted_date ON transactions (deleted_at, date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions (account_id);
CREATE INDEX IF NOT EXISTS idx_people_ledger_deleted ON people_ledger (deleted_at);
CREATE INDEX IF NOT EXISTS idx_loans_status_deleted ON loans (status, deleted_at);
CREATE INDEX IF NOT EXISTS idx_categories_deleted ON categories (deleted_at);
