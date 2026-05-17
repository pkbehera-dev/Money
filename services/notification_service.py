from database.connection import get_db_connection
from datetime import datetime

class NotificationService:
    @staticmethod
    def get_notifications(unread_only=False, limit=20):
        conn = get_db_connection()
        query = "SELECT * FROM notifications WHERE deleted_at IS NULL"
        if unread_only:
            query += " AND read_status = 0"
        query += " ORDER BY created_at DESC LIMIT ?"
        rows = conn.execute(query, (limit,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add_notification(title, message, n_type='info', priority='medium', action_link=None):
        conn = get_db_connection()
        # Check for duplicates of same message in last 24 hours to avoid spam
        exists = conn.execute('''
            SELECT id FROM notifications 
            WHERE title = ? AND message = ? AND created_at > datetime('now', '-1 day') AND deleted_at IS NULL
        ''', (title, message)).fetchone()
        
        if not exists:
            conn.execute('''
                INSERT INTO notifications (title, message, type, priority, action_link)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, message, n_type, priority, action_link))
            conn.commit()
        conn.close()

    @staticmethod
    def mark_as_read(notif_id):
        conn = get_db_connection()
        conn.execute("UPDATE notifications SET read_status = 1 WHERE id = ?", (notif_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_notification(notif_id):
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE notifications SET deleted_at = ? WHERE id = ?", (now, notif_id))
        conn.commit()
        conn.close()

    @staticmethod
    def clear_all():
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE notifications SET deleted_at = ? WHERE read_status = 1", (now,))
        conn.commit()
        conn.close()

    @staticmethod
    def check_all_triggers():
        """
        Force runs all engine checks (Budgets, Goals, Subscriptions).
        """
        from services.budget_service import BudgetService
        from services.goal_service import GoalService
        from services.subscription_service import SubscriptionService
        
        # 1. Budgets
        budget_notifs = BudgetService.check_budget_thresholds()
        for n in budget_notifs:
            NotificationService.add_notification(n['title'], n['message'], n['type'], n['priority'], action_link='/budgets')
            
        # 2. Subscriptions
        sub_notifs = SubscriptionService.get_upcoming_renewals(days=3)
        for s in sub_notifs:
            msg = f"Subscription {s['name']} is due on {s['next_due_date']} (₹{s['amount']})"
            NotificationService.add_notification("Subscription Renewal", msg, "subscription", "high", action_link='/subscriptions')
            
        # 3. Goals
        goals = GoalService.get_all_goals()
        for g in goals:
            if g['status'] == 'completed':
                # Only notify if achieved recently (within 24h)
                NotificationService.add_notification("Goal Achieved! 🎉", f"Congratulations! You've reached your target for '{g['name']}'.", "success", "high", action_link='/goals')
            elif g['tracking_text'] == 'Behind':
                NotificationService.add_notification("Goal Behind Schedule", f"'{g['name']}' is falling behind. You may need to increase contributions.", "warning", "medium", action_link='/goals')
            
        # 4. Asset Value Tracking
        NotificationService.check_asset_value_updates()
            
        return True

    @staticmethod
    def check_asset_value_updates():
        conn = get_db_connection()
        today = datetime.now()
        assets = conn.execute("SELECT * FROM assets WHERE depreciation_enabled = 1 AND deleted_at IS NULL").fetchall()
        
        for asset in assets:
            try:
                p_date = datetime.strptime(asset['purchase_date'], '%Y-%m-%d')
                # Trigger if it's the same day of the month
                if today.day == p_date.day:
                    msg = f"Time for monthly value update for {asset['name']}. Current book value: ₹{asset['current_value']}"
                    NotificationService.add_notification(
                        "Asset Value Update", 
                        msg, 
                        "info", 
                        "medium", 
                        action_link="/assets"
                    )
            except Exception as e:
                print(f"Error checking asset {asset['name']}: {e}")
                continue
        conn.close()
