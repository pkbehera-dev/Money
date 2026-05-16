from database.connection import get_db_connection
from datetime import datetime, timedelta

class SubscriptionService:
    @staticmethod
    def get_all_subscriptions():
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM subscriptions WHERE deleted_at IS NULL ORDER BY next_due_date").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def create_subscription(name, amount, billing_cycle, next_due_date, category, payment_source=None, auto_renew=1, notes=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO subscriptions (name, amount, billing_cycle, next_due_date, category, payment_source, auto_renew, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, amount, billing_cycle, next_due_date, category, payment_source, auto_renew, notes))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    @staticmethod
    def get_subscription_stats():
        conn = get_db_connection()
        rows = conn.execute("SELECT amount, billing_cycle FROM subscriptions WHERE status = 'active' AND deleted_at IS NULL").fetchall()
        conn.close()
        
        monthly_total = 0
        yearly_total = 0
        
        for row in rows:
            amt = row['amount']
            cycle = row['billing_cycle']
            
            if cycle == 'Monthly':
                monthly_total += amt
                yearly_total += amt * 12
            elif cycle == 'Weekly':
                monthly_total += amt * 4.33
                yearly_total += amt * 52
            elif cycle == 'Quarterly':
                monthly_total += amt / 3
                yearly_total += amt * 4
            elif cycle == 'Yearly':
                monthly_total += amt / 12
                yearly_total += amt
                
        return {
            "monthly_total": monthly_total,
            "yearly_total": yearly_total,
            "count": len(rows)
        }

    @staticmethod
    def get_upcoming_renewals(days=7):
        conn = get_db_connection()
        target_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        rows = conn.execute("SELECT * FROM subscriptions WHERE status = 'active' AND next_due_date <= ? AND deleted_at IS NULL ORDER BY next_due_date", (target_date,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def delete_subscription(sub_id):
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE subscriptions SET deleted_at = ? WHERE id = ?", (now, sub_id))
        conn.commit()
        conn.close()
