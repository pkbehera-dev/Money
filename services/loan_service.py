from database.connection import get_db_connection
import datetime

class LoanService:
    @staticmethod
    def get_all_loans(filters: dict = None):
        conn = get_db_connection()
        query = "SELECT * FROM loans WHERE 1=1"
        if filters and filters.get('status'):
            query += f" AND status = '{filters['status']}'"
        
        loans = [dict(r) for r in conn.execute(query).fetchall()]
        
        for loan in loans:
            # DYNAMIC CALCULATION: Sum all payments from the ledger
            paid_amount = conn.execute("SELECT SUM(amount) FROM loan_payments WHERE loan_id = ?", (loan['id'],)).fetchone()[0] or 0
            loan['paid_amount'] = paid_amount
            loan['remaining'] = loan['total_to_pay'] - paid_amount
            loan['progress'] = (paid_amount / loan['total_to_pay'] * 100) if loan['total_to_pay'] > 0 else 0
            loan['monthly_emi'] = (loan['total_to_pay'] / loan['tenure']) if loan['tenure'] > 0 else 0
            
            # Fetch last payment
            last_p = conn.execute("SELECT amount, date FROM loan_payments WHERE loan_id = ? ORDER BY date DESC LIMIT 1", (loan['id'],)).fetchone()
            loan['last_payment'] = dict(last_p) if last_p else None
            
            # Fetch history
            history = conn.execute("SELECT * FROM loan_payments WHERE loan_id = ? ORDER BY date DESC", (loan['id'],)).fetchall()
            loan['history'] = [dict(h) for h in history]
            
        conn.close()
        return loans

    @staticmethod
    def create_loan(name: str, principal: float, total_to_pay: float, tenure: int, due_date: int, start_date: str = None, initial_paid: float = 0, account_id: any = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Save the loan first
        if not start_date:
            start_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
        cursor.execute('''
            INSERT INTO loans (name, principal, total_to_pay, tenure, due_date, start_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, principal, total_to_pay, tenure, due_date, start_date))
        loan_id = cursor.lastrowid
        conn.commit()
        conn.close() 

        # 2. Record principal receipt if account selected (SILENT)
        if account_id and str(account_id).strip() != "" and principal > 0:
            act_id = None
            c_id = None
            raw_id = str(account_id).strip()
            
            if raw_id.startswith('card_'):
                c_id = int(raw_id.replace('card_', ''))
            else:
                try:
                    act_id = int(raw_id)
                except ValueError:
                    act_id = None

            if act_id or c_id:
                TransactionService.add_transaction(
                    type='income',
                    amount=principal,
                    category='Loan Principal Migration',
                    date=datetime.datetime.now().strftime('%Y-%m-%d'),
                    account_id=act_id,
                    card_id=c_id,
                    notes=f"Principal received for {name}",
                    tags="Silent"
                )

        # 3. Create initial payment record if there's an existing balance
        if initial_paid > 0:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO loan_payments (loan_id, amount, date, type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (loan_id, initial_paid, datetime.datetime.now().strftime('%Y-%m-%d'), 'Manual Adjustment', 'Initial paid balance at creation'))
            conn.commit()
            conn.close()
            
        return loan_id

    @staticmethod
    def add_payment(loan_id: int, amount: float, date: str, p_type: str, notes: str, account_id: any = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        # 1. Save payment record first
        conn.execute('''
            INSERT INTO loan_payments (loan_id, amount, date, type, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (loan_id, amount, date, p_type, notes))
        conn.commit()
        
        # 2. Fetch loan name
        loan_name = conn.execute("SELECT name FROM loans WHERE id = ?", (loan_id,)).fetchone()[0]
        conn.close()
        
        # 3. Record the transaction separately
        if account_id and account_id != "":
            act_id = None
            c_id = None
            if str(account_id).startswith('card_'):
                c_id = int(str(account_id).replace('card_', ''))
            else:
                act_id = int(account_id)
                
            TransactionService.add_transaction(
                type='expense',
                amount=amount,
                category='Loan Repayment',
                date=date,
                account_id=act_id,
                card_id=c_id,
                notes=f"Payment for {loan_name}: {p_type} - {notes}"
            )
            
    @staticmethod
    def delete_loan(loan_id: int):
        from datetime import datetime
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE loans SET deleted_at = ? WHERE id = ?", (now, loan_id))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_loan_by_id(loan_id: int):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_loan(loan_id: int, name: str, principal: float, total_to_pay: float, tenure: int, due_date: int):
        conn = get_db_connection()
        conn.execute("""
            UPDATE loans SET name = ?, principal = ?, total_to_pay = ?, tenure = ?, due_date = ?
            WHERE id = ?
        """, (name, principal, total_to_pay, tenure, due_date, loan_id))
        conn.commit()
        conn.close()


    @staticmethod
    def foreclose_loan(loan_id: int, account_id: int = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        loan = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        total_to_pay = loan["total_to_pay"]
        loan_name = loan["name"]
        
        # Calculate remaining
        paid = conn.execute("SELECT SUM(amount) FROM loan_payments WHERE loan_id = ?", (loan_id,)).fetchone()[0] or 0
        conn.close() # Close read connection
        
        remaining = total_to_pay - paid
        if remaining > 0:
            # Record final payment
            LoanService.add_payment(loan_id, remaining, datetime.datetime.now().strftime("%Y-%m-%d"), "Foreclosure", "Loan foreclosed and closed.", account_id)
            
        conn = get_db_connection()
        conn.execute("UPDATE loans SET status = \"closed\" WHERE id = ?", (loan_id,))
        conn.commit()
        conn.close()

