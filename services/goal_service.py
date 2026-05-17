from database.connection import get_db_connection
from datetime import datetime

class GoalService:
    @staticmethod
    def get_all_goals():
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM goals WHERE deleted_at IS NULL ORDER BY status, priority DESC").fetchall()
        conn.close()
        
        goals = []
        now = datetime.now()
        for row in rows:
            g = dict(row)
            target_amount = g.get('target_amount') or 0.0
            current_amount = g.get('current_amount') or 0.0
            g['target_amount'] = float(target_amount)
            g['current_amount'] = float(current_amount)
            g['progress'] = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0
            g['remaining'] = g['target_amount'] - g['current_amount']
            
            # Dynamic Tracking Status
            status_text = "On Track"
            status_icon = "ph-trend-up"
            status_class = "text-success"
            
            if g['status'] == 'completed':
                status_text = "Achieved"
                status_icon = "ph-check-circle"
            elif g['target_date']:
                try:
                    created_at = datetime.strptime(g['created_at'], '%Y-%m-%d %H:%M:%S')
                    target_date = datetime.strptime(g['target_date'], '%Y-%m-%d')
                    
                    total_days = (target_date - created_at).days
                    elapsed_days = (now - created_at).days
                    
                    if total_days > 0:
                        expected_progress = (elapsed_days / total_days) * 100
                        if g['progress'] < expected_progress - 5: # 5% buffer
                            status_text = "Behind"
                            status_icon = "ph-warning"
                            status_class = "text-danger"
                        elif g['progress'] > expected_progress + 10:
                            status_text = "Ahead"
                            status_icon = "ph-rocket-launch"
                            status_class = "text-primary"
                except Exception:
                    pass
            
            g['tracking_text'] = status_text
            g['tracking_icon'] = status_icon
            g['tracking_class'] = status_class
            goals.append(g)
        return goals

    @staticmethod
    def create_goal(name, target_amount, target_date, category, priority='medium', notes=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO goals (name, target_amount, target_date, category, priority, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, target_amount, target_date, category, priority, notes))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    @staticmethod
    def get_goal_by_id(goal_id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        conn.close()
        if row:
            g = dict(row)
            g['progress'] = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] and g['target_amount'] > 0 else 0
            return g
        return None

    @staticmethod
    def contribute_to_goal(goal_id, amount, account_id=None):
        from services.transaction_service import TransactionService
        
        # 1. Update Goal and get Name
        conn = get_db_connection()
        conn.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (amount, goal_id))
        goal = conn.execute("SELECT name FROM goals WHERE id = ?", (goal_id,)).fetchone()
        goal_name = goal['name'] if goal else "Unknown Goal"
        conn.commit()
        conn.close() # Close BEFORE calling TransactionService
        
        # 2. Record Transaction if account provided
        if account_id:
            TransactionService.add_transaction(
                type='expense',
                amount=amount,
                category='Goal Contribution',
                date=datetime.now().strftime('%Y-%m-%d'),
                account_id=account_id,
                notes=f"Contribution to goal: {goal_name}",
                tags="Goal"
            )

        # 3. Check completion and update status
        conn = get_db_connection()
        goal_status = conn.execute("SELECT current_amount, target_amount FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if goal_status and goal_status['target_amount'] and goal_status['current_amount'] >= goal_status['target_amount']:
            conn.execute("UPDATE goals SET status = 'completed' WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def withdraw_from_goal(goal_id, amount, account_id=None):
        from services.transaction_service import TransactionService
        
        # 1. Check if enough money in goal
        conn = get_db_connection()
        goal = conn.execute("SELECT name, current_amount FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not goal:
            conn.close()
            return False, "Goal not found"
            
        if goal['current_amount'] < amount:
            conn.close()
            return False, f"Insufficient balance in goal (Current: ₹{goal['current_amount']:.2f})"
        
        goal_name = goal['name']
        conn.close()

        # 2. Deduct from Goal
        conn = get_db_connection()
        conn.execute("UPDATE goals SET current_amount = current_amount - ?, status = 'active' WHERE id = ?", (amount, goal_id))
        conn.commit()
        conn.close() # Close BEFORE calling TransactionService
        
        # 3. Record Transaction (Income to account)
        if account_id:
            TransactionService.add_transaction(
                type='income',
                amount=amount,
                category='Goal Withdrawal',
                date=datetime.now().strftime('%Y-%m-%d'),
                account_id=account_id,
                notes=f"Emergency withdrawal from goal: {goal_name}",
                tags="Goal, Emergency"
            )

        return True, "Success"

    @staticmethod
    def update_goal(goal_id, **kwargs):
        conn = get_db_connection()
        fields = [f"{k} = ?" for k in kwargs.keys()]
        params = list(kwargs.values())
        params.append(goal_id)
        conn.execute(f"UPDATE goals SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    @staticmethod
    def delete_goal(goal_id):
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE goals SET deleted_at = ? WHERE id = ?", (now, goal_id))
        conn.commit()
        conn.close()
