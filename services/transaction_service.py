from database.connection import get_db_connection
from models.transaction import Transaction
from services.account_service import AccountService

class TransactionService:
    @staticmethod
    def get_all_transactions(filters: dict = None, sort_by: str = 'date_desc'):
        """Fetches transactions with optional filtering and sorting."""
        conn = get_db_connection()
        query = """
            SELECT t.*, a1.name as account_name, a2.name as to_account_name
            FROM transactions t
            LEFT JOIN accounts a1 ON t.account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            WHERE 1=1 
            AND t.deleted_at IS NULL
            AND t.category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND t.tags NOT LIKE '%Silent%'
        """
        params = []

        if filters:
            if filters.get('type'):
                query += " AND t.type = ?"
                params.append(filters['type'])
            if filters.get('category'):
                query += " AND t.category = ?"
                params.append(filters['category'])
            if filters.get('account_id'):
                query += " AND t.account_id = ?"
                params.append(filters['account_id'])
            if filters.get('date_from'):
                query += " AND t.date >= ?"
                params.append(filters['date_from'])
            if filters.get('date_to'):
                query += " AND t.date <= ?"
                params.append(filters['date_to'])
            if filters.get('min_amount'):
                query += " AND t.amount >= ?"
                params.append(float(filters['min_amount']))
            if filters.get('max_amount'):
                query += " AND t.amount <= ?"
                params.append(float(filters['max_amount']))
            if filters.get('search'):
                query += " AND (t.category LIKE ? OR t.notes LIKE ? OR t.tags LIKE ?)"
                search_q = f"%{filters['search']}%"
                params.extend([search_q, search_q, search_q])

        # Sorting
        sort_map = {
            'date_desc': 'ORDER BY date DESC',
            'date_asc': 'ORDER BY date ASC',
            'amount_desc': 'ORDER BY amount DESC',
            'amount_asc': 'ORDER BY amount ASC',
            'category': 'ORDER BY category ASC'
        }
        query += " " + sort_map.get(sort_by, 'ORDER BY date DESC')

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [Transaction(**dict(row)) for row in rows]

    @staticmethod
    def add_transaction(type: str, amount: float, category: str, date: str, 
                        account_id: int = None, to_account_id: int = None, 
                        notes: str = None, tags: str = None, transfer_fee: float = 0.0,
                        card_id: int = None, person_id: int = None, emi_data: dict = None):
        """Adds a transaction and updates balances where necessary."""
        from services.loan_service import LoanService
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. If it's an EMI, we automatically create a loan entry
        if emi_data and type == 'expense':
            # Principal is the transaction amount
            total_to_pay = emi_data['total_to_pay']
            loan_name = f"{category} ({notes[:20] if notes else 'No Notes'})"
            # create_loan(name, principal, total_to_pay, tenure, due_date, initial_paid, account_id)
            LoanService.create_loan(
                name=loan_name,
                principal=amount,
                total_to_pay=total_to_pay,
                tenure=emi_data['tenure'],
                due_date=emi_data['due_date'],
                initial_paid=0,
                account_id=None # The transaction itself handles the principal deduction if any
            )
            # Update notes to link back
            notes = f"[EMI PLAN] {notes or ''}"
            tags = f"{tags or ''} Silent".strip()
        
        cursor.execute('''
            INSERT INTO transactions (type, amount, category, date, account_id, to_account_id, card_id, person_id, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (type, amount, category, date, account_id, to_account_id, card_id, person_id, notes, tags))
        
        # TRANSACTION DRIVEN: Only update liquid account balances
        # Credit Card and Loan balances are calculated dynamically from history
        if account_id:
            if type == 'income':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            elif type == 'expense':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            elif type == 'transfer' and to_account_id:
                # Deduct from source account
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount + transfer_fee, account_id))
                # If target is another account, add to it
                if to_account_id > 0:
                    conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, to_account_id))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    @staticmethod
    def get_transaction_by_id(tx_id: int):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def clear_all():
        conn = get_db_connection()
        conn.execute("DELETE FROM transactions")
        conn.commit()
        conn.close()

    @staticmethod
    def delete_transaction(tx_id: int):
        conn = get_db_connection()
        tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not tx or tx['deleted_at']:
            conn.close()
            return
            
        # REVERSE BALANCE
        if tx['account_id']:
            if tx['type'] == 'income':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (tx['amount'], tx['account_id']))
            elif tx['type'] == 'expense':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (tx['amount'], tx['account_id']))
            elif tx['type'] == 'transfer':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (tx['amount'], tx['account_id']))
                if tx['to_account_id']:
                    conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (tx['amount'], tx['to_account_id']))
        
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE transactions SET deleted_at = ? WHERE id = ?", (now, tx_id))
        conn.commit()
        conn.close()

    @staticmethod
    def restore_transaction(tx_id: int):
        conn = get_db_connection()
        tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not tx or not tx['deleted_at']:
            conn.close()
            return
            
        # RE-APPLY BALANCE
        amount = tx['amount']
        account_id = tx['account_id']
        to_account_id = tx['to_account_id']
        type = tx['type']

        if account_id:
            if type == 'income':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            elif type == 'expense':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            elif type == 'transfer':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
                if to_account_id:
                    conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, to_account_id))
        
        conn.execute("UPDATE transactions SET deleted_at = NULL WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def update_transaction(tx_id: int, type: str, amount: float, category: str, date: str, 
                          account_id: int, to_account_id: int = None, notes: str = None, tags: str = None):
        # 1. Delete and re-apply is the safest way for balance integrity
        TransactionService.delete_transaction(tx_id)
        # 2. Add as "new" but keep the ID (or just use the existing add logic)
        # Actually, let's just use the add_transaction logic but allow specifying ID
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (id, type, amount, category, date, account_id, to_account_id, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tx_id, type, amount, category, date, account_id, to_account_id, notes, tags))
        
        if account_id:
            if type == 'income':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            elif type == 'expense':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            elif type == 'transfer' and to_account_id:
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
                if to_account_id > 0:
                    conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, to_account_id))
        
        conn.commit()
        conn.close()
    @staticmethod
    def get_categories(type_filter='expense'):
        from services.category_service import CategoryService
        categories = CategoryService.get_all_categories(type_filter)
        return [c['name'] for c in categories]
