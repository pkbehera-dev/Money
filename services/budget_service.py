from database.connection import get_db_connection
from datetime import datetime, timedelta

class BudgetService:
    @staticmethod
    def get_all_budgets():
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM budgets WHERE deleted_at IS NULL ORDER BY status, name").fetchall()
        conn.close()
        
        budgets = []
        for row in rows:
            b = dict(row)
            b['spent'], b['progress'], b['remaining'], b['prediction'] = BudgetService.calculate_budget_progress(b)
            
            # Health Logic
            if b['progress'] < 70: b['health'] = 'safe'
            elif b['progress'] < 90: b['health'] = 'warning'
            else: b['health'] = 'danger'
            
            budgets.append(b)
        return budgets

    @staticmethod
    def get_budget_insights(budgets):
        insights = []
        now = datetime.now()
        
        # 1. Prediction Insights
        for b in budgets:
            if b['prediction'] > b['amount']:
                over_by = b['prediction'] - b['amount']
                insights.append({
                    'type': 'danger',
                    'icon': 'ph-trend-up',
                    'text': f"You may exceed your {b['name']} budget by ₹{over_by:.0f} this month based on current trends."
                })
            elif b['progress'] > 85:
                 insights.append({
                    'type': 'warning',
                    'icon': 'ph-warning',
                    'text': f"Critical: {b['name']} budget is at {b['progress']:.0f}%. Tighten spending here."
                })

        # 2. General Insights
        total_budgeted = sum(b['amount'] for b in budgets)
        total_spent = sum(b['spent'] for b in budgets)
        
        if total_spent < (total_budgeted * 0.4) and now.day > 15:
            insights.append({
                'type': 'success',
                'icon': 'ph-check-circle',
                'text': "Excellent! You are well under budget for this stage of the month."
            })

        if not insights:
            insights.append({
                'type': 'info',
                'icon': 'ph-info',
                'text': "Spending speed is normal. No immediate budget risks detected."
            })
            
        return insights[:3] # Show top 3

    @staticmethod
    def create_budget(name, b_type, target_id, amount, period, start_date=None, end_date=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO budgets (name, type, target_id, amount, period, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, b_type, target_id, amount, period, start_date, end_date))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    @staticmethod
    def calculate_budget_progress(budget):
        """
        Calculates how much has been spent for a given budget based on its type and period.
        """
        now = datetime.now()
        start_date = None
        end_date = None

        # Determine date range based on period
        if budget['period'] == 'Monthly':
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            # End of month
            if now.month == 12:
                end_date = now.replace(year=now.year+1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = now.replace(month=now.month+1, day=1) - timedelta(days=1)
            end_date = end_date.strftime('%Y-%m-%d')
        elif budget['period'] == 'Weekly':
            start_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            end_date = (now + timedelta(days=6 - now.weekday())).strftime('%Y-%m-%d')
        elif budget['period'] == 'Yearly':
            start_date = now.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date = now.replace(month=12, day=31).strftime('%Y-%m-%d')
        elif budget['period'] == 'Custom':
            start_date = budget['start_date']
            end_date = budget['end_date']

        # Query transactions
        conn = get_db_connection()
        query = "SELECT SUM(amount) FROM transactions WHERE type = 'expense' AND date BETWEEN ? AND ? AND deleted_at IS NULL"
        params = [start_date, end_date]

        if budget['type'] == 'Category':
            query += " AND category = ?"
            params.append(budget['target_id'])
        elif budget['type'] == 'Account':
            query += " AND account_id = ?"
            params.append(budget['target_id'])

        row = conn.execute(query, params).fetchone()
        conn.close()

        spent = row[0] or 0.0
        remaining = budget['amount'] - spent
        progress = (spent / budget['amount'] * 100) if budget['amount'] > 0 else 0
        
        # Calculate Prediction
        prediction = spent
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            total_days = (ed - sd).days + 1
            days_passed = (datetime.now() - sd).days + 1
            if days_passed > 0 and days_passed < total_days:
                prediction = (spent / days_passed) * total_days
        except:
            pass

        return spent, progress, remaining, prediction

    @staticmethod
    def check_budget_thresholds():
        """
        Runs periodically (via analytics check) to trigger notifications.
        """
        budgets = BudgetService.get_all_budgets()
        notifications = []
        
        for b in budgets:
            if b['status'] != 'active': continue
            
            prog = b['progress']
            thresholds = [50, 70, 90, 100]
            
            for t in thresholds:
                # We use a naming convention for unique notifications to avoid duplicates: budget_{id}_{threshold}
                # Check if this specific threshold alert was already sent this period
                # (For simplicity here, we'll just check if it's currently exceeding)
                
                if prog >= t:
                    label = f"Budget Alert: {b['name']}"
                    msg = f"You have reached {prog:.1f}% of your {b['period'].lower()} budget ({b['name']})."
                    if prog >= 100:
                        msg = f"CRITICAL: Budget '{b['name']}' exceeded by ₹{abs(b['remaining']):.2f}!"
                    
                    notifications.append({
                        'title': label,
                        'message': msg,
                        'priority': 'high' if prog >= 100 else 'medium',
                        'type': 'budget'
                    })
        return notifications
