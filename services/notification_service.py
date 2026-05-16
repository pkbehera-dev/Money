import sqlite3
from database.connection import DB_PATH
from datetime import datetime, timedelta

class NotificationService:
    @staticmethod
    def get_db_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def add_notification(cls, title, message, n_type, priority, action_link=""):
        """Adds a notification if a similar one doesn't exist for today."""
        conn = cls.get_db_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Prevent duplicate notifications for the same event on the same day
        exists = conn.execute('''
            SELECT 1 FROM notifications 
            WHERE title = ? AND date(created_at) = ?
        ''', (title, today)).fetchone()
        
        if not exists:
            conn.execute('''
                INSERT INTO notifications (title, message, type, priority, action_link)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, message, n_type, priority, action_link))
            conn.commit()
        conn.close()

    @classmethod
    def check_all_triggers(cls):
        """Main engine that runs in background to scan for triggers."""
        conn = cls.get_db_connection()
        today = datetime.now()
        
        # 1. Loan Reminders
        loans = conn.execute("SELECT * FROM loans WHERE status = 'active'").fetchall()
        for loan in loans:
            due_day = loan['due_date']
            due_date = datetime(today.year, today.month, due_day)
            days_diff = (due_date - today).days
            
            # Progress-based notifications
            progress = (loan['paid_amount'] / loan['total_to_pay'] * 100) if loan['total_to_pay'] > 0 else 0
            if progress >= 90 and progress < 100:
                cls.add_notification("Loan Almost Completed", f"Congratulations! Your {loan['name']} is {progress:.1f}% paid off.", "loan", "medium", "/loans")

            if days_diff == 1:
                cls.add_notification(f"Loan Payment Due", f"A payment for {loan['name']} is due tomorrow.", "loan", "high", "/loans")
            elif days_diff == 0:
                cls.add_notification(f"Loan Payment Due Today", f"Don't forget your payment for {loan['name']} today!", "loan", "critical", "/loans")
            elif days_diff < 0:
                cls.add_notification(f"Loan Overdue", f"{loan['name']} payment is overdue by {abs(days_diff)} days.", "loan", "critical", "/loans")

        # 2. Credit Card Reminders
        cards = conn.execute("SELECT * FROM credit_cards WHERE outstanding > 0").fetchall()
        for card in cards:
            usage = (card['outstanding'] / card['card_limit']) * 100
            if usage > 85:
                cls.add_notification("High Card Usage", f"{card['name']} usage is at {usage:.1f}%.", "card", "high", "/cards")
            
            due_day = card['due_date']
            if due_day:
                due_date = datetime(today.year, today.month, due_day)
                days_diff = (due_date - today).days
                if days_diff <= 3 and days_diff >= 0:
                    cls.add_notification("Card Payment Due", f"{card['name']} bill of ₹{card['outstanding']} due in {days_diff} days.", "card", "high", "/cards")

        # 3. Lent/Borrow Reminders
        ledger = conn.execute("SELECT * FROM people_ledger WHERE total_amount > paid_amount").fetchall()
        for entry in ledger:
            balance = entry['total_amount'] - entry['paid_amount']
            if entry['type'] == 'lent' and balance > 1000:
                cls.add_notification("Pending Dues", f"{entry['person_name']} still owes you ₹{balance}.", "ledger", "medium", "/ledger")

        # 4. Financial Warnings
        # Check if expenses > income this month
        month_start = today.strftime('%Y-%m-01')
        row = conn.execute('''
            SELECT 
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as inc,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as exp
            FROM transactions WHERE date >= ?
        ''', (month_start,)).fetchone()
        if row and row['exp'] > row['inc'] and row['inc'] > 0:
            cls.add_notification("Budget Warning", "Expenses have exceeded your income this month!", "warning", "critical", "/")

        conn.close()

    @classmethod
    def get_notifications(cls, unread_only=False):
        conn = cls.get_db_connection()
        if unread_only:
            rows = conn.execute("SELECT * FROM notifications WHERE read_status = 0 ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @classmethod
    def mark_as_read(cls, n_id):
        conn = cls.get_db_connection()
        conn.execute("UPDATE notifications SET read_status = 1 WHERE id = ?", (n_id,))
        conn.commit()
        conn.close()

    @classmethod
    def delete_notification(cls, n_id):
        conn = cls.get_db_connection()
        conn.execute("DELETE FROM notifications WHERE id = ?", (n_id,))
        conn.commit()
        conn.close()
