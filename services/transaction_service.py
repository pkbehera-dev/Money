from database.connection import get_db_connection
from models.transaction import Transaction
from services.account_service import AccountService

class TransactionService:
    @staticmethod
    def get_all_transactions(filters: dict = None, sort_by: str = 'date_desc'):
        """Fetches transactions with optional filtering and sorting."""
        conn = get_db_connection()
        query = """
            SELECT t.*, a1.name as account_name, a2.name as to_account_name, c.name as card_name
            FROM transactions t
            LEFT JOIN accounts a1 ON t.account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            LEFT JOIN credit_cards c ON t.card_id = c.id
            WHERE 1=1 
            AND t.deleted_at IS NULL
            AND t.category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            AND COALESCE(t.tags, '') NOT LIKE '%Silent%'
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
                acc_val = str(filters['account_id'])
                if acc_val.startswith('A'):
                    acc_id = int(acc_val[1:])
                    query += " AND (t.account_id = ? OR t.to_account_id = ?)"
                    params.extend([acc_id, acc_id])
                elif acc_val.startswith('C'):
                    card_id = int(acc_val[1:])
                    query += " AND t.card_id = ?"
                    params.append(card_id)
                else:
                    try:
                        acc_id = int(acc_val)
                        query += " AND (t.account_id = ? OR t.to_account_id = ?)"
                        params.extend([acc_id, acc_id])
                    except ValueError:
                        pass
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
                query += " AND (t.category LIKE ? OR t.notes LIKE ? OR t.tags LIKE ? OR a1.name LIKE ? OR a2.name LIKE ? OR c.name LIKE ?)"
                search_q = f"%{filters['search']}%"
                params.extend([search_q, search_q, search_q, search_q, search_q, search_q])

        # Sorting
        sort_map = {
            'date_desc': 'ORDER BY date DESC, id DESC',
            'date_asc': 'ORDER BY date ASC, id ASC',
            'amount_desc': 'ORDER BY amount DESC',
            'amount_asc': 'ORDER BY amount ASC',
            'category': 'ORDER BY category ASC'
        }
        query += " " + sort_map.get(sort_by, 'ORDER BY date DESC, id DESC')

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
        
        # Ensure account_id / card_id / to_account_id are parsed if strings are passed
        if isinstance(account_id, str) and account_id:
            if account_id.startswith('A'): 
                account_id = int(account_id[1:])
            elif account_id.startswith('C'): 
                card_id = int(account_id[1:])
                account_id = None
            else:
                try:
                    account_id = int(account_id)
                except ValueError:
                    account_id = None

        if isinstance(to_account_id, str) and to_account_id:
            if to_account_id.startswith('A'): 
                to_account_id = int(to_account_id[1:])
            elif to_account_id.startswith('C'): 
                card_id = int(to_account_id[1:])
                to_account_id = -1
            else:
                try:
                    to_account_id = int(to_account_id)
                except ValueError:
                    to_account_id = None
        
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions (type, amount, category, date, account_id, to_account_id, card_id, person_id, notes, tags, transfer_fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (type, amount, category, date, account_id, to_account_id, card_id, person_id, notes, tags, transfer_fee))
        
        # TRANSACTION DRIVEN: Only update liquid account balances
        # Credit Card and Loan balances are calculated dynamically from history
        if account_id and account_id > 0:
            if type == 'income':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            elif type == 'expense':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            elif type == 'transfer':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount + transfer_fee, account_id))
        
        if type == 'transfer' and to_account_id and to_account_id > 0:
            conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, to_account_id))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        # Trigger real-time summaries refresh and alert checks
        from services.analytics_service import AnalyticsService
        AnalyticsService.refresh_summaries()
        
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
        if tx['account_id'] and tx['account_id'] > 0:
            if tx['type'] == 'income':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (tx['amount'], tx['account_id']))
            elif tx['type'] == 'expense':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (tx['amount'], tx['account_id']))
            elif tx['type'] == 'transfer':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (tx['amount'] + (tx['transfer_fee'] or 0.0), tx['account_id']))
        
        if tx['type'] == 'transfer' and tx['to_account_id'] and tx['to_account_id'] > 0:
            conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (tx['amount'], tx['to_account_id']))
        
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE transactions SET deleted_at = ? WHERE id = ?", (now, tx_id))
        conn.commit()
        conn.close()
        
        # Trigger real-time summaries refresh and alert checks
        from services.analytics_service import AnalyticsService
        AnalyticsService.refresh_summaries()

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
        transfer_fee = tx['transfer_fee'] or 0.0

        if account_id and account_id > 0:
            if type == 'income':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            elif type == 'expense':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            elif type == 'transfer':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount + transfer_fee, account_id))
        
        if type == 'transfer' and to_account_id and to_account_id > 0:
            conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, to_account_id))
        
        conn.execute("UPDATE transactions SET deleted_at = NULL WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        
        # Trigger real-time summaries refresh and alert checks
        from services.analytics_service import AnalyticsService
        AnalyticsService.refresh_summaries()

    @staticmethod
    def update_transaction(tx_id: int, type: str, amount: float, category: str, date: str, 
                          account_id: int = None, to_account_id: int = None, notes: str = None, 
                          tags: str = None, card_id: int = None, transfer_fee: float = 0.0):
        # 1. Fetch the existing transaction to preserve fields
        conn = get_db_connection()
        tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not tx:
            conn.close()
            return
        
        person_id = tx['person_id']
        recurring_id = tx['recurring_id']
        if card_id is None:
            card_id = tx['card_id']
        conn.close()

        # 2. Reverse balance and soft-delete
        TransactionService.delete_transaction(tx_id)
        
        # 3. Physically delete to avoid UNIQUE constraint violation on re-inserting the same ID
        conn = get_db_connection()
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        
        # 4. Insert updated transaction with the same ID and preserved fields
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (id, type, amount, category, date, account_id, to_account_id, card_id, person_id, recurring_id, notes, tags, transfer_fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tx_id, type, amount, category, date, account_id, to_account_id, card_id, person_id, recurring_id, notes, tags, transfer_fee))
        
        # 5. Apply the new balances
        if account_id and account_id > 0:
            if type == 'income':
                conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            elif type == 'expense':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            elif type == 'transfer':
                conn.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount + transfer_fee, account_id))
        
        if type == 'transfer' and to_account_id and to_account_id > 0:
            conn.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, to_account_id))
        
        conn.commit()
        conn.close()
        
        # Trigger real-time summaries refresh and alert checks
        from services.analytics_service import AnalyticsService
        AnalyticsService.refresh_summaries()
    @staticmethod
    def get_categories(type_filter='expense'):
        from services.category_service import CategoryService
        categories = CategoryService.get_all_categories(type_filter)
        return [c['name'] for c in categories]
