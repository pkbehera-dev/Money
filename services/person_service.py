from database.connection import get_db_connection
from datetime import datetime

class PersonService:
    @staticmethod
    def get_all_people(filters: dict = None):
        conn = get_db_connection()
        query = "SELECT * FROM people_ledger WHERE 1=1"
        people = [dict(r) for r in conn.execute(query).fetchall()]
        
        for person in people:
            # DYNAMIC CALCULATION: Sum all repayment transactions
            # Type 'income' means they paid me back (for Lent) or I received money (for Borrow)
            # Actually, let's keep it simple: any transaction linked to person_id is a movement.
            # Initial amount is recorded as the 'base' in the people_ledger for simplicity,
            # but repayments must be in the transactions table.
            
            repayments = conn.execute("SELECT SUM(amount) FROM transactions WHERE person_id = ?", (person['id'],)).fetchone()[0] or 0
            person['paid_amount'] = repayments
            person['remaining'] = person['total_amount'] - repayments
            
        conn.close()
        return people

    @staticmethod
    def add_person(name: str, ledger_type: str, total_amount: float, notes: str = None, date: str = None, account_id: int = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO people_ledger (person_name, type, total_amount, notes)
            VALUES (?, ?, ?, ?)
        ''', (name, ledger_type, total_amount, notes))
        person_id = cursor.lastrowid
        
        # TRANSACTION DRIVEN: Affect liquid balance
        if account_id and total_amount > 0:
            tx_type = 'expense' if ledger_type == 'lent' else 'income'
            TransactionService.add_transaction(
                type=tx_type,
                amount=total_amount,
                category='Interpersonal Debt',
                date=date or datetime.now().strftime('%Y-%m-%d'),
                account_id=account_id,
                notes=f"{ledger_type.capitalize()} to/from {name}: {notes}"
            )
        
        conn.commit()
        conn.close()
        return person_id

    @staticmethod
    def record_payment(person_id: int, amount: float, account_id: int = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        
        person = conn.execute("SELECT * FROM people_ledger WHERE id = ?", (person_id,)).fetchone()
        
        # TRANSACTION DRIVEN: Create a transaction record
        if account_id:
            # If I lent money, repayment is 'income'
            # If I borrowed, repayment is 'expense'
            tx_type = 'income' if person['type'] == 'lent' else 'expense'
            TransactionService.add_transaction(
                type=tx_type,
                amount=amount,
                category='Debt Repayment',
                date=datetime.now().strftime('%Y-%m-%d'),
                account_id=account_id,
                notes=f"Repayment for {person['person_name']}"
            )

        conn.commit()
        conn.close()

    @staticmethod
    def settle_person(person_id: int, account_id: int = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        person = conn.execute("SELECT * FROM people_ledger WHERE id = ?", (person_id,)).fetchone()
        
        # Calculate remaining
        repayments = conn.execute("SELECT SUM(amount) FROM transactions WHERE person_id = ?", (person_id,)).fetchone()[0] or 0
        remaining = person["total_amount"] - repayments
        
        if remaining > 0:
            PersonService.record_payment(person_id, remaining, account_id)
            
        conn.execute("UPDATE people_ledger SET status = \"closed\" WHERE id = ?", (person_id,))
        conn.commit()
        conn.close()

