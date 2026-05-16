import datetime
from database.connection import get_db_connection
from services.transaction_service import TransactionService

class RecurringService:
    @staticmethod
    def process_due_transactions():
        """
        Checks for any recurring transactions that are due and creates standard transactions for them.
        Updates the next_due_date.
        """
        conn = get_db_connection()
        today = datetime.date.today().isoformat()
        
        # Get all recurring transactions that are not paused and are due
        rows = conn.execute(
            'SELECT * FROM recurring_transactions WHERE is_paused = 0 AND next_due_date <= ?', 
            (today,)
        ).fetchall()

        for row in rows:
            # 1. Create the transaction
            TransactionService.add_transaction(
                type=row['type'],
                amount=row['amount'],
                category=row['category'],
                date=today, # The date it was generated
                account_id=row['account_id'],
                to_account_id=row['to_account_id'],
                notes=f"{row['notes']} (Auto-generated)",
                tags=row['tags']
            )

            # 2. Calculate next due date
            current_due = datetime.date.fromisoformat(row['next_due_date'])
            interval = row['interval']
            
            if interval == 'Daily':
                next_due = current_due + datetime.timedelta(days=1)
            elif interval == 'Weekly':
                next_due = current_due + datetime.timedelta(days=7)
            elif interval == 'Monthly':
                # Simplified monthly addition (doesn't perfectly handle end of month edge cases)
                month = current_due.month
                year = current_due.year + month // 12
                month = month % 12 + 1
                day = min(current_due.day, [31, 29 if year % 4 == 0 and not year % 400 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                next_due = datetime.date(year, month, day)
            elif interval == 'Yearly':
                next_due = datetime.date(current_due.year + 1, current_due.month, current_due.day)
            elif interval == 'Custom':
                next_due = current_due + datetime.timedelta(days=row['custom_interval_days'])
            else:
                next_due = current_due + datetime.timedelta(days=30) # Fallback

            # 3. Update the recurring transaction record
            conn.execute(
                'UPDATE recurring_transactions SET next_due_date = ?, last_generated_date = ? WHERE id = ?',
                (next_due.isoformat(), today, row['id'])
            )
        
        conn.commit()
        conn.close()
