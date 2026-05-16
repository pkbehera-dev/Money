CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    balance REAL DEFAULT 0.0,
    notes TEXT
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
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(to_account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS credit_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    card_limit REAL NOT NULL,
    outstanding REAL DEFAULT 0.0,
    billing_date INTEGER, -- day of month
    due_date INTEGER -- day of month
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    notes TEXT
);

-- Summary Tables for Performance
CREATE TABLE IF NOT EXISTS daily_summaries (
    date TEXT PRIMARY KEY,
    income_total REAL DEFAULT 0,
    expense_total REAL DEFAULT 0,
    tx_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS monthly_summaries (
    month TEXT PRIMARY KEY, -- YYYY-MM
    income_total REAL DEFAULT 0,
    expense_total REAL DEFAULT 0,
    savings REAL DEFAULT 0,
    loan_repayments REAL DEFAULT 0,
    credit_usage REAL DEFAULT 0,
    tx_count INTEGER DEFAULT 0
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
    action_link TEXT
);
