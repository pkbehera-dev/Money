import sqlite3
import os
import random
from datetime import datetime, timedelta

def seed_database():
    print("Starting 5-year database seeding...")
    
    # 1. Paths and Connection
    db_path = os.path.join(os.path.dirname(__file__), 'finance.db')
    from database.connection import init_db
    init_db()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 2. Reset the database
    print("Resetting database tables...")
    tables = [
        'accounts', 'transactions', 'recurring_transactions', 'credit_cards', 
        'loans', 'loan_payments', 'people_ledger', 'daily_summaries', 
        'monthly_summaries', 'category_summaries', 'transaction_archive', 
        'notifications', 'budgets', 'assets', 'goals', 'subscriptions', 
        'health_history', 'networth_history', 'yearly_summaries', 'weekly_summaries'
    ]
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table}")
            cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        except sqlite3.OperationalError as e:
            print(f"Warning clearing {table}: {e}")

    conn.commit()

    # 3. Seed Default Categories
    print("Seeding categories...")
    default_categories = [
        ('Salary', 'income', '#4caf50', 'ph-briefcase'),
        ('Investment', 'income', '#2196f3', 'ph-chart-line-up'),
        ('Gift', 'income', '#9c27b0', 'ph-gift'),
        ('Freelance', 'income', '#009688', 'ph-laptop'),
        ('Food', 'expense', '#ff9800', 'ph-fork-knife'),
        ('Bills', 'expense', '#f44336', 'ph-receipt'),
        ('Shopping', 'expense', '#e91e63', 'ph-shopping-bag'),
        ('Entertainment', 'expense', '#673ab7', 'ph-popcorn'),
        ('Travel', 'expense', '#03a9f4', 'ph-airplane-takeoff'),
        ('Health', 'expense', '#e91e63', 'ph-first-aid'),
        ('Education', 'expense', '#3f51b5', 'ph-student'),
        ('Other', 'expense', '#9e9e9e', 'ph-dots-three-circle'),
        ('Loan Repayment', 'expense', '#ff5722', 'ph-bank'),
        ('Debt Repayment', 'income', '#8bc34a', 'ph-handshake'),
        ('Debt Repayment', 'expense', '#e51c23', 'ph-handshake'),
        ('Goal Contribution', 'expense', '#00bcd4', 'ph-target'),
        ('Goal Withdrawal', 'income', '#ffeb3b', 'ph-safe')
    ]
    cur.executemany("INSERT INTO categories (name, type, color, icon) VALUES (?, ?, ?, ?)", default_categories)

    # 4. Seed Accounts
    print("Seeding accounts...")
    accounts_data = [
        (1, 'Cash in Hand', 'Cash', 7420.00, 'Physical cash in wallet'),
        (2, 'HDFC Salary Account', 'Bank account', 68400.00, 'Primary active checking account'),
        (3, 'SBI High-Yield Savings', 'Bank account', 245000.00, 'Emergency fund & long-term savings'),
        (4, 'Paytm Wallet', 'Wallet', 3100.00, 'Digital wallet for quick local payments')
    ]
    cur.executemany("INSERT INTO accounts (id, name, type, balance, notes) VALUES (?, ?, ?, ?, ?)", accounts_data)

    # 5. Seed Credit Cards
    print("Seeding credit cards...")
    cards_data = [
        (1, 'ICICI Amazon Pay', 150000.00, 0.0, 15, 5, 'active', 150000.00),
        (2, 'HDFC Regalia Black', 300000.00, 0.0, 20, 10, 'active', 300000.00)
    ]
    cur.executemany("INSERT INTO credit_cards (id, name, card_limit, outstanding, billing_date, due_date, status, credit_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", cards_data)

    # 6. Seed Loans
    print("Seeding loans & payments (active HDFC Home Loan & completed SBI Car Loan)...")
    # A. SBI Car Loan (Principal: 8,00,000, Total: 9,20,000, closed, 60-month tenure, started 5 years ago)
    cur.execute("""
        INSERT INTO loans (id, name, principal, total_to_pay, paid_amount, tenure, due_date, status, start_date)
        VALUES (1, 'SBI Car Loan', 800000.00, 920000.00, 920000.00, 60, 5, 'closed', '2021-05-15')
    """)
    
    # Generate 60 EMI payments for Car Loan (finished)
    car_payments = []
    car_emi = 920000.00 / 60 # 15333.33
    car_start = datetime(2021, 6, 5)
    for i in range(60):
        pay_date = (car_start + timedelta(days=i*30.4375)).strftime('%Y-%m-%d')
        car_payments.append((1, car_emi, pay_date, 'EMI', f"Car Loan EMI Payment {i+1}/60"))
    cur.executemany("INSERT INTO loan_payments (loan_id, amount, date, type, notes) VALUES (?, ?, ?, ?, ?)", car_payments)

    # B. HDFC Home Loan (Principal: 25,00,000, Total: 35,00,000, active, 180-month tenure, started 2 years ago)
    cur.execute("""
        INSERT INTO loans (id, name, principal, total_to_pay, paid_amount, tenure, due_date, status, start_date)
        VALUES (2, 'HDFC Home Loan', 2500000.00, 3500000.00, 0.0, 180, 10, 'active', '2024-05-10')
    """)
    
    # Generate 24 EMI payments for Home Loan (active)
    home_payments = []
    home_emi = 3500000.00 / 180 # 19444.44
    home_start = datetime(2024, 6, 10)
    for i in range(24):
        pay_date = (home_start + timedelta(days=i*30.4375)).strftime('%Y-%m-%d')
        home_payments.append((2, home_emi, pay_date, 'EMI', f"Home Loan EMI Payment {i+1}/180"))
    cur.executemany("INSERT INTO loan_payments (loan_id, amount, date, type, notes) VALUES (?, ?, ?, ?, ?)", home_payments)
    
    # Update paid amounts in loans table
    cur.execute("UPDATE loans SET paid_amount = ? WHERE id = 2", (home_emi * 24,))

    # 7. Seed Interpersonal Ledger (People)
    print("Seeding people ledger...")
    cur.execute("""
        INSERT INTO people_ledger (id, person_name, type, total_amount, paid_amount, notes, status)
        VALUES (1, 'Rahul Sharma', 'lent', 15000.00, 5000.00, 'Lent for bike service & insurance', 'active')
    """)
    cur.execute("""
        INSERT INTO people_ledger (id, person_name, type, total_amount, paid_amount, notes, status)
        VALUES (2, 'Priya Patel', 'borrowed', 8000.00, 2000.00, 'Borrowed for office birthday event', 'active')
    """)

    # 8. Seed Assets
    print("Seeding assets...")
    assets_data = [
        ('Residential Plot (Pune)', 'Property', 3500000.00, 3850000.00, '2022-01-10', 0, 'Investment plot in growth sector'),
        ('10g Gold Coin', 'Gold', 68000.00, 78500.00, '2023-10-24', 0, 'Purchased on Dhanteras'),
        ('MacBook Pro M3 Max', 'Electronics', 199000.00, 145000.00, '2024-08-12', 1, 'Development workstation - depreciating')
    ]
    cur.executemany("INSERT INTO assets (name, category, purchase_value, current_value, purchase_date, depreciation_enabled, notes) VALUES (?, ?, ?, ?, ?, ?, ?)", assets_data)

    # 9. Seed Goals
    print("Seeding goals...")
    today_str = datetime.today().strftime('%Y-%m-%d')
    six_months_ago = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S')
    goals_data = [
        ('Emergency Fund', 200000.00, 150000.00, (datetime.today() + timedelta(days=200)).strftime('%Y-%m-%d'), 'Savings', 'high', '6 months of living expenses buffer', 'active', six_months_ago),
        ('Europe Summer Trip', 300000.00, 45000.00, (datetime.today() + timedelta(days=90)).strftime('%Y-%m-%d'), 'Purchase', 'medium', 'Behind schedule - need to optimize savings rate', 'active', six_months_ago),
        ('Electric Scooter', 150000.00, 120000.00, (datetime.today() + timedelta(days=120)).strftime('%Y-%m-%d'), 'Purchase', 'low', 'Ahead of schedule - on track for early delivery', 'active', six_months_ago)
    ]
    cur.executemany("INSERT INTO goals (name, target_amount, current_amount, target_date, category, priority, notes, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", goals_data)

    # 10. Seed Subscriptions
    print("Seeding subscriptions...")
    subs_data = [
        ('Netflix Premium', 649.00, 'Monthly', (datetime.today() + timedelta(days=3)).strftime('%Y-%m-%d'), 'Entertainment', 'Paytm Wallet', 1, 'Family sharing package', 'active'),
        ('Spotify Premium Family', 179.00, 'Monthly', (datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d'), 'Entertainment', 'ICICI Amazon Pay', 1, 'Auto-renew active', 'active'),
        ('Amazon Prime Annual', 1499.00, 'Yearly', (datetime.today() + timedelta(days=15)).strftime('%Y-%m-%d'), 'Shopping', 'HDFC Salary Account', 1, 'Free delivery and video streaming', 'active')
    ]
    cur.executemany("INSERT INTO subscriptions (name, amount, billing_cycle, next_due_date, category, payment_source, auto_renew, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", subs_data)

    # 11. Seed Recurring Transactions
    print("Seeding recurring transactions...")
    recur_data = [
        ('expense', 15000.00, 'Bills', 2, None, 'Monthly Rent Transfer', 'Monthly', (datetime.today() + timedelta(days=8)).strftime('%Y-%m-%d'), 0),
        ('transfer', 10000.00, 'Investment', 2, 3, 'Monthly Savings Automation', 'Monthly', (datetime.today() + timedelta(days=14)).strftime('%Y-%m-%d'), 0)
    ]
    cur.executemany("INSERT INTO recurring_transactions (type, amount, category, account_id, to_account_id, notes, interval, next_due_date, is_paused) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", recur_data)

    # 12. Seed Notifications
    print("Seeding notifications...")
    notifs_data = [
        ('Budget Alert: Food & Dining', 'Groceries & dining has exceeded 85% of your allocated monthly limit.', 'budget', 'high', 0, '/budgets'),
        ('Upcoming Renewal', 'Your subscription for Netflix Premium (₹649) is due in 3 days.', 'subscription', 'medium', 0, '/subscriptions'),
        ('Goal Progress Milestone', 'Excellent! You have saved 75% towards your Emergency Fund goal.', 'goal', 'low', 1, '/goals')
    ]
    cur.executemany("INSERT INTO notifications (title, message, type, priority, read_status, action_link) VALUES (?, ?, ?, ?, ?, ?)", notifs_data)

    # 13. Seed Health History (90 Days)
    print("Seeding financial health history (90 days)...")
    today = datetime.today().date()
    health_data = []
    for i in range(90):
        h_date = (today - timedelta(days=90-i)).isoformat()
        score = int(58 + (i * 0.3) + random.uniform(-2.0, 2.0))
        score = min(max(score, 0), 100)
        status = "Healthy" if score >= 80 else "Fair" if score >= 60 else "At Risk"
        reasons = '{"savings_rate": "Good", "debt_ratio": "Improving", "budget_adherence": "Average"}'
        health_data.append((h_date, score, status, reasons))
    cur.executemany("INSERT INTO health_history (date, score, status, reasons) VALUES (?, ?, ?, ?)", health_data)

    # 14. Seed Net Worth History (60 Months = 5 Years)
    print("Seeding historical net worth snapshots (5 years)...")
    nw_data = []
    for i in range(60):
        month_date = (today - timedelta(days=(59-i)*30.4375)).replace(day=1).isoformat()
        # Assets rising from 2,300,000 to 4,380,000 over 5 years
        assets = float(2300000 + i * 35000 + random.uniform(-10000, 10000))
        # Liabilities: started high due to loan, dropping gradually
        liabilities = float(1050000 - i * 8500 + random.uniform(-4000, 4000))
        if i >= 36: # Home loan principal is added 2 years ago (24 months ago)
            liabilities += 2500000 - (i - 36) * 19444.44
            assets += 3500000 # House value added to assets
        networth = assets - liabilities
        nw_data.append((month_date, assets, liabilities, networth))
    cur.executemany("INSERT INTO networth_history (date, assets, liabilities, networth) VALUES (?, ?, ?, ?)", nw_data)

    # 15. Seed Transactions (5-Year Historical Time-series Stream)
    print("Generating 5 years of historical raw transactions...")
    tx_list = []
    start_timeline = today - timedelta(days=5*365)
    
    for i in range(5*365 + 1):
        curr_day = start_timeline + timedelta(days=i)
        day_str = curr_day.strftime('%Y-%m-%d')
        
        # A. Monthly Salary (28th of every month)
        if curr_day.day == 28:
            # Salary rises over the years
            salary = 95000.00
            if curr_day.year == 2022: salary = 105000.00
            elif curr_day.year == 2023: salary = 112000.00
            elif curr_day.year == 2024: salary = 118000.00
            elif curr_day.year >= 2025: salary = 125000.00
            tx_list.append(('income', salary, 'Salary', day_str, 2, None, None, None, 'Monthly Salary Credit', 'Salary, Income'))
            
        # B. Monthly Investment Dividends (15th of every month)
        if curr_day.day == 15:
            tx_list.append(('income', 4500.00, 'Investment', day_str, 3, None, None, None, 'HDFC Dividend payout', 'Dividends, Investment'))
            
        # C. Monthly Rent Payment (1st of every month)
        if curr_day.day == 1:
            tx_list.append(('expense', 15000.00, 'Bills', day_str, 2, None, None, None, 'Monthly Rent Transfer', 'Rent, Bills'))
            
        # D. Monthly Car Loan EMI (5th of every month, for 5 years: June 2021 - May 2026)
        if curr_day.day == 5 and curr_day >= datetime(2021, 6, 5).date() and curr_day <= datetime(2026, 5, 5).date():
            tx_list.append(('expense', car_emi, 'Loan Repayment', day_str, 2, None, None, None, 'SBI Car Loan EMI Payment', 'Loan, EMI, Car'))

        # E. Monthly Home Loan EMI (10th of every month, for last 2 years: June 2024 - May 2026)
        if curr_day.day == 10 and curr_day >= datetime(2024, 6, 10).date() and curr_day <= datetime(2026, 5, 10).date():
            tx_list.append(('expense', home_emi, 'Loan Repayment', day_str, 2, None, None, None, 'HDFC Home Loan EMI Payment', 'Loan, EMI, Home'))

        # F. Interpersonal debt repayments (Rahul / Priya - in May 2026)
        if curr_day.year == 2026 and curr_day.month == 5 and curr_day.day == 10:
            tx_list.append(('income', 5000.00, 'Debt Repayment', day_str, 2, None, None, 1, 'Partial repayment from Rahul Sharma', 'Rahul, Repayment'))
        if curr_day.year == 2026 and curr_day.month == 5 and curr_day.day == 12:
            tx_list.append(('expense', 2000.00, 'Debt Repayment', day_str, 2, None, None, 2, 'Partial repayment to Priya Patel', 'Priya, Repayment'))

        # G. Monthly Subscriptions
        if curr_day.day == 12: # Netflix
            tx_list.append(('expense', 649.00, 'Entertainment', day_str, 4, None, None, None, 'Netflix Monthly Subscription', 'Netflix, Entertainment'))
        if curr_day.day == 18: # Spotify
            tx_list.append(('expense', 179.00, 'Entertainment', day_str, None, None, 1, None, 'Spotify Premium charged to Card', 'Spotify, Subscription'))

        # H. Daily/Weekly Food & Dining (very frequent)
        if random.random() < 0.35: # 35% chance every day
            amt = round(random.uniform(150, 1100), 2)
            src = random.choice([('account', 1), ('account', 4), ('card', 1)])
            acc_id = src[1] if src[0] == 'account' else None
            card_id = src[1] if src[0] == 'card' else None
            notes = random.choice(['Groceries from supermarket', 'Zomato food delivery', 'Dinner at restaurant', 'Local cafe snack'])
            tx_list.append(('expense', amt, 'Food', day_str, acc_id, None, card_id, None, notes, 'Food, Groceries'))

        # I. Fuel / Travel
        if i % 3 == 0:
            amt = round(random.uniform(400, 1400), 2)
            src = random.choice([('account', 1), ('account', 4), ('card', 1)])
            acc_id = src[1] if src[0] == 'account' else None
            card_id = src[1] if src[0] == 'card' else None
            notes = random.choice(['Petrol top-up', 'Uber ride', 'Metro smartcard load'])
            tx_list.append(('expense', amt, 'Travel', day_str, acc_id, None, card_id, None, notes, 'Travel, Commute'))

        # J. Weekend Shopping & Entertainment
        if curr_day.weekday() == 5: # Saturday
            if random.random() < 0.6:
                amt = round(random.uniform(800, 5000), 2)
                src = random.choice([('account', 2), ('card', 1), ('card', 2)])
                acc_id = src[1] if src[0] == 'account' else None
                card_id = src[1] if src[0] == 'card' else None
                cat = random.choice(['Shopping', 'Entertainment'])
                notes = 'Movie ticket & dinner' if cat == 'Entertainment' else 'Weekend retail shopping'
                tx_list.append(('expense', amt, cat, day_str, acc_id, None, card_id, None, notes, f'Weekend, {cat}'))

        # K. Random bills between 5th and 10th
        if curr_day.day == 8:
            amt = round(random.uniform(2000, 4500), 2)
            tx_list.append(('expense', amt, 'Bills', day_str, 2, None, None, None, 'Electricity bill payment', 'Electricity, Bills'))
        if curr_day.day == 10:
            tx_list.append(('expense', 999.00, 'Bills', day_str, 4, None, None, None, 'Broadband Internet', 'Internet, Bills'))

        # L. Monthly Transfers HDFC -> SBI
        if curr_day.day == 10 and random.random() < 0.5:
            tx_list.append(('transfer', 15000.00, 'Investment', day_str, 2, 3, None, None, 'Automated Monthly Savings', 'Savings, Transfer'))

    cur.executemany("""
        INSERT INTO transactions (type, amount, category, date, account_id, to_account_id, card_id, person_id, notes, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tx_list)
    
    # Update interpersonal ledger paid counts from database actuals
    cur.execute("UPDATE people_ledger SET paid_amount = 5000.00 WHERE id = 1")
    cur.execute("UPDATE people_ledger SET paid_amount = 2000.00 WHERE id = 2")

    conn.commit()
    conn.close()
    print(f"Direct insertion of {len(tx_list)} raw transactions completed successfully.")

    # 16. Seed Budgets
    print("Seeding budget allocations...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    budgets_data = [
        ('Overall Monthly Budget', 'Overall', None, 45000.00, 'Monthly', today.replace(day=1).isoformat(), 'active'),
        ('Groceries & Food Budget', 'Category', 'Food', 12000.00, 'Monthly', today.replace(day=1).isoformat(), 'active'),
        ('Shopping Allowance', 'Category', 'Shopping', 8000.00, 'Monthly', today.replace(day=1).isoformat(), 'active'),
        ('Entertainment cap', 'Category', 'Entertainment', 5000.00, 'Monthly', today.replace(day=1).isoformat(), 'active'),
        ('Cash Account Budget', 'Account', '1', 6000.00, 'Monthly', today.replace(day=1).isoformat(), 'active')
    ]
    cur.executemany("INSERT INTO budgets (name, type, target_id, amount, period, start_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)", budgets_data)
    conn.commit()
    conn.close()

    # 17. Perform Rebuild and Retention Partitioning via Engine
    print("Triggering historical aggregates rebuild across 5 years...")
    try:
        from services.historical_summary_service import HistoricalSummaryEngine
        from services.net_worth_service import NetWorthService
        from services.notification_service import NotificationService
        
        # A. Rebuild all summaries across the full 5-year timeline (rebuilds daily, weekly, monthly, yearly tables!)
        print("Executing HistoricalSummaryEngine.rebuild_all_summaries()...")
        HistoricalSummaryEngine.rebuild_all_summaries()
        
        # B. Run archival partitioning (moves raw transactions older than 12 months to transaction_archive)
        print("Executing HistoricalSummaryEngine.archive_older_transactions(12)...")
        HistoricalSummaryEngine.archive_older_transactions(12)
        
        # C. Capture current Net Worth snapshot
        print("Capturing live Net Worth snapshot...")
        NetWorthService.update_snapshot()
        
        # D. Re-evaluate notifications and triggers
        print("Validating budget threshold triggers...")
        NotificationService.check_all_triggers()
        
        print("Database historical engines processed successfully!")
    except Exception as e:
        print(f"Warning during service calculations: {e}")
        import traceback
        traceback.print_exc()

    print("5-Year Database Seeding Completed Successfully! The timeline is fully populated.")

if __name__ == "__main__":
    seed_database()
