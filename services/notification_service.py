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
        conn.execute("UPDATE notifications SET deleted_at = ? WHERE deleted_at IS NULL", (now,))
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
            
        # 2. Subscriptions & 3. Goals
        conn = get_db_connection()
        sub_notifs = SubscriptionService.get_upcoming_renewals(days=3)
        to_notify_subs = []
        for s in sub_notifs:
            msg = f"Subscription {s['name']} is due on {s['next_due_date']} (₹{s['amount']})"
            exists = conn.execute("""
                SELECT id FROM notifications 
                WHERE type = 'subscription' AND message = ? AND deleted_at IS NULL
            """, (msg,)).fetchone()
            if not exists:
                to_notify_subs.append(s)
            
        goals = GoalService.get_all_goals()
        to_notify_goals = []
        for g in goals:
            if g['status'] == 'completed':
                exists = conn.execute("""
                    SELECT id FROM notifications 
                    WHERE type = 'goal_achieved' AND message LIKE ? AND deleted_at IS NULL
                """, (f"%'{g['name']}'%",)).fetchone()
                if not exists:
                    to_notify_goals.append({
                        "title": "Goal Achieved! 🎉", 
                        "message": f"Congratulations! You've reached your target for '{g['name']}'.", 
                        "type": "goal_achieved", 
                        "priority": "high"
                    })
            elif g['tracking_text'] == 'Behind':
                exists = conn.execute("""
                    SELECT id FROM notifications 
                    WHERE type = 'goal_behind' AND message LIKE ? AND created_at > datetime('now', '-7 days') AND deleted_at IS NULL
                """, (f"%'{g['name']}'%",)).fetchone()
                if not exists:
                    to_notify_goals.append({
                        "title": "Goal Behind Schedule", 
                        "message": f"'{g['name']}' is falling behind. You may need to increase contributions.", 
                        "type": "goal_behind", 
                        "priority": "medium"
                    })
            
        conn.close()

        # Execute all insertions on separate short-lived transactions
        for n in budget_notifs:
            NotificationService.add_notification(n['title'], n['message'], n['type'], n['priority'], action_link='/budgets')

        for s in to_notify_subs:
            msg = f"Subscription {s['name']} is due on {s['next_due_date']} (₹{s['amount']})"
            NotificationService.add_notification("Subscription Renewal", msg, "subscription", "high", action_link='/subscriptions')

        for g_notif in to_notify_goals:
            NotificationService.add_notification(
                g_notif["title"], 
                g_notif["message"], 
                g_notif["type"], 
                g_notif["priority"], 
                action_link='/goals'
            )
        
        # 5. Credit Card Utilization
        try:
            from services.credit_card_service import CreditCardService
            cards = CreditCardService.get_all_cards()
            conn_cc = get_db_connection()
            for card in cards:
                if card.get('deleted_at') is not None:
                    continue
                usage_pct = card.get('usage_pct', 0)
                if usage_pct >= 80:
                    title = f"High Credit Card Utilization: {card['name']}"
                    msg = f"Credit card '{card['name']}' utilization is at {usage_pct:.1f}% (₹{card['outstanding']:.0f}/₹{card['card_limit']:.0f})."
                    # Check if warned in last 7 days to avoid spam
                    exists = conn_cc.execute("""
                        SELECT id FROM notifications 
                        WHERE type = 'credit_card' AND title = ? AND created_at > datetime('now', '-7 days') AND deleted_at IS NULL
                    """, (title,)).fetchone()
                    if not exists:
                        NotificationService.add_notification(
                            title, msg, 'credit_card', 
                            'high' if usage_pct >= 90 else 'medium', 
                            action_link='/credit-cards'
                        )
            conn_cc.close()
        except Exception as e:
            print(f"Error checking credit card utilization triggers: {e}")
        
        # 4. Asset Value Tracking
        NotificationService.check_asset_value_updates()
            
        return True

    @staticmethod
    def check_asset_value_updates():
        conn = get_db_connection()
        today = datetime.now()
        assets = conn.execute("SELECT * FROM assets WHERE depreciation_enabled = 1 AND deleted_at IS NULL").fetchall()
        assets_list = [dict(a) for a in assets]
        conn.close()
        
        for asset in assets_list:
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
