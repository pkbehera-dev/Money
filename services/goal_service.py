from database.connection import get_db_connection
from datetime import datetime

class GoalService:
    @staticmethod
    def get_all_goals():
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM goals WHERE deleted_at IS NULL ORDER BY status, priority DESC").fetchall()
        conn.close()
        
        goals = []
        for row in rows:
            g = dict(row)
            g['progress'] = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0
            g['remaining'] = g['target_amount'] - g['current_amount']
            # Simple estimate: target_amount / avg savings
            # For now we'll just return the pre-calculated fields
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
    def contribute_to_goal(goal_id, amount):
        conn = get_db_connection()
        conn.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (amount, goal_id))
        
        # Check if completed
        goal = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if goal['current_amount'] >= goal['target_amount']:
            conn.execute("UPDATE goals SET status = 'completed' WHERE id = ?", (goal_id,))
            
        conn.commit()
        conn.close()
        return True

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
