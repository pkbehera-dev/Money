import datetime
from database.connection import get_db_connection

from services.report_service import ReportService
from services.net_worth_service import NetWorthService

class FinanceService:
    @staticmethod
    def get_dashboard_metrics():
        conn = get_db_connection()
        
        # 1. Current Stats
        row = conn.execute('SELECT SUM(balance) as total FROM accounts').fetchone()
        total_balance = row['total'] if row['total'] else 0.0
        
        today = datetime.date.today()
        month_start = f"{today.year}-{today.month:02d}-01"
        
        # Current Month Income/Expense
        row_inc = conn.execute("""
            SELECT SUM(amount) as total FROM transactions 
            WHERE type='income' AND date >= ?
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            AND deleted_at IS NULL
        """, (month_start,)).fetchone()
        monthly_income = row_inc['total'] if row_inc['total'] else 0.0

        row_exp = conn.execute("""
            SELECT SUM(amount) as total FROM transactions 
            WHERE type='expense' AND date >= ?
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            AND deleted_at IS NULL
        """, (month_start,)).fetchone()
        monthly_expense = row_exp['total'] if row_exp['total'] else 0.0

        # 2. Previous Month Comparison (for percentages)
        first_of_this_month = datetime.date(today.year, today.month, 1)
        last_month_date = first_of_this_month - datetime.timedelta(days=1)
        last_month_start = f"{last_month_date.year}-{last_month_date.month:02d}-01"
        last_month_end = f"{last_month_date.year}-{last_month_date.month:02d}-31"

        row_inc_prev = conn.execute("""
            SELECT SUM(amount) as total FROM transactions 
            WHERE type='income' AND date BETWEEN ? AND ?
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            AND deleted_at IS NULL
        """, (last_month_start, last_month_end)).fetchone()
        prev_income = row_inc_prev['total'] if row_inc_prev['total'] else 0.0

        row_exp_prev = conn.execute("""
            SELECT SUM(amount) as total FROM transactions 
            WHERE type='expense' AND date BETWEEN ? AND ?
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            AND deleted_at IS NULL
        """, (last_month_start, last_month_end)).fetchone()
        prev_expense = row_exp_prev['total'] if row_exp_prev['total'] else 0.0

        # Percentage calculations
        def calc_pct(cur, prev):
            if prev == 0: return 0.0
            return ((cur - prev) / prev) * 100

        income_pct = calc_pct(monthly_income, prev_income)
        expense_pct = calc_pct(monthly_expense, prev_expense)

        # Lent / Borrowed
        row_lent = conn.execute("SELECT SUM(total_amount - paid_amount) as total FROM people_ledger WHERE type='lent' AND deleted_at IS NULL").fetchone()
        lent_amount = row_lent['total'] if row_lent['total'] else 0.0

        row_borrowed = conn.execute("SELECT SUM(total_amount - paid_amount) as total FROM people_ledger WHERE type='borrowed' AND deleted_at IS NULL").fetchone()
        borrowed_amount = row_borrowed['total'] if row_borrowed['total'] else 0.0

        transactions = conn.execute("""
            SELECT * FROM transactions 
            WHERE category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            AND deleted_at IS NULL
            ORDER BY date DESC LIMIT 5
        """).fetchall()
        # 3. Dynamic Card Reminders
        raw_cards = conn.execute("SELECT * FROM credit_cards WHERE status = 'active'").fetchall()
        cards = []
        for c in raw_cards:
            purchases = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id = ? AND type = 'expense' AND COALESCE(tags, '') NOT LIKE '%Silent%'", (c['id'],)).fetchone()[0] or 0
            payments = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id = ? AND type = 'transfer'", (c['id'],)).fetchone()[0] or 0
            outstanding = purchases - payments
            if outstanding > 0:
                card_dict = dict(c)
                card_dict['outstanding'] = outstanding
                cards.append(card_dict)
        loans = conn.execute("SELECT * FROM loans WHERE status = 'active' AND deleted_at IS NULL").fetchall()

        conn.close()

        # Net Worth Calculation
        nw_total, nw_assets, nw_liabilities = NetWorthService.calculate_net_worth()
        nw_change = NetWorthService.get_monthly_change()

        return {
            'total_balance': total_balance,
            'monthly_income': monthly_income,
            'monthly_expense': monthly_expense,
            'income_pct': income_pct,
            'expense_pct': expense_pct,
            'net_savings': monthly_income - monthly_expense,
            'lent_amount': lent_amount,
            'borrowed_amount': borrowed_amount,
            'recent_transactions': [dict(t) for t in transactions],
            'card_reminders': [dict(c) for c in cards],
            'loan_reminders': [dict(l) for l in loans],
            'chart_category': ReportService.get_category_spending(),
            'chart_trends': ReportService.get_monthly_trends(),
            'net_worth_stats': {
                'total': nw_total,
                'assets': nw_assets,
                'liabilities': nw_liabilities,
                'change_pct': nw_change
            }
        }
