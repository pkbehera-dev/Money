from database.connection import get_db_connection
import datetime

class ReportService:
    @staticmethod
    def get_category_spending():
        """Returns data for the pie chart: Category vs Total Amount."""
        conn = get_db_connection()
        # Only expenses for this month
        today = datetime.date.today()
        month_start = f"{today.year}-{today.month:02d}-01"
        
        query = '''
            SELECT category, SUM(amount) as total 
            FROM transactions 
            WHERE type='expense' AND date >= ?
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            GROUP BY category
        '''
        rows = conn.execute(query, (month_start,)).fetchall()
        conn.close()
        
        labels = [row['category'] or 'Uncategorized' for row in rows]
        data = [row['total'] for row in rows]
        return {"labels": labels, "data": data}

    @staticmethod
    def get_monthly_trends():
        """Returns data for the line chart: Daily income vs expense for the last 30 days."""
        conn = get_db_connection()
        # Last 30 days
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        query = '''
            SELECT date, 
                   SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
            FROM transactions 
            WHERE date >= ?
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(tags, '') NOT LIKE '%Silent%'
            GROUP BY date
            ORDER BY date ASC
        '''
        rows = conn.execute(query, (start_date.isoformat(),)).fetchall()
        conn.close()
        
        labels = [row['date'] for row in rows]
        income_data = [row['income'] for row in rows]
        expense_data = [row['expense'] for row in rows]
        
        return {
            "labels": labels,
            "income": income_data,
            "expense": expense_data
        }
