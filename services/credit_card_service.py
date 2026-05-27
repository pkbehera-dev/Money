from database.connection import get_db_connection
from datetime import datetime

class CreditCardService:
    @staticmethod
    def get_all_cards(filters: dict = None):
        conn = get_db_connection()
        query = "SELECT * FROM credit_cards WHERE 1=1"
        cards = [dict(r) for r in conn.execute(query).fetchall()]
        
        for card in cards:
            # 1. Purchases (Direct expenses)
            purchases = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id = ? AND type = 'expense' AND deleted_at IS NULL", (card['id'],)).fetchone()[0] or 0
            # 2. Cash Withdrawals / Transfers FROM Card (Increases debt)
            withdrawals = conn.execute("SELECT SUM(amount + COALESCE(transfer_fee, 0.0)) FROM transactions WHERE card_id = ? AND type = 'transfer' AND account_id IS NULL AND to_account_id IS NOT NULL AND deleted_at IS NULL", (card['id'],)).fetchone()[0] or 0
            # 3. Bill Payments (Transfers TO Card from a bank account) (Decreases debt)
            payments = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id = ? AND type = 'transfer' AND account_id IS NOT NULL AND deleted_at IS NULL", (card['id'],)).fetchone()[0] or 0
            
            card['outstanding'] = (purchases + withdrawals) - payments
            card['available'] = card['card_limit'] - card['outstanding']
            card['usage_pct'] = (card['outstanding'] / card['card_limit'] * 100) if card['card_limit'] > 0 else 0

        conn.close()
        return cards

    @staticmethod
    def add_card(name: str, limit: float, outstanding: float, billing_date: int, due_date: int, account_id: int = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO credit_cards (name, card_limit, outstanding, billing_date, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, limit, 0, billing_date, due_date, 'active'))
        card_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # TRANSACTION DRIVEN: Record the initial outstanding as a transaction
        if outstanding > 0:
            # We record this as an expense linked to the card to establish the debt
            TransactionService.add_transaction(
                type='expense',
                amount=outstanding,
                category='Credit Card Entry',
                date=datetime.now().strftime("%Y-%m-%d"),
                account_id=account_id, # If provided, it deducts from bank. If None, it just adds to card debt.
                notes=f"Initial outstanding balance for {name}",
                card_id=card_id
            )
            
        return card_id
        
    @staticmethod
    def log_purchase(card_id: int, amount: float):
        conn = get_db_connection()
        conn.execute('UPDATE credit_cards SET outstanding = outstanding + ? WHERE id = ?', (amount, card_id))
        conn.commit()
        conn.close()

    @staticmethod
    def log_payment(card_id: int, amount: float):
        conn = get_db_connection()
        conn.execute('UPDATE credit_cards SET outstanding = outstanding - ? WHERE id = ?', (amount, card_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_card(card_id: int):
        from datetime import datetime
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE credit_cards SET deleted_at = ? WHERE id = ?", (now, card_id))
        conn.commit()
        conn.close()


    @staticmethod
    def get_card_by_id(card_id: int):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM credit_cards WHERE id = ?", (card_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_card(card_id: int, name: str, limit: float, billing_date: int, due_date: int):
        conn = get_db_connection()
        conn.execute("""
            UPDATE credit_cards SET name = ?, card_limit = ?, billing_date = ?, due_date = ?
            WHERE id = ?
        """, (name, limit, billing_date, due_date, card_id))
        conn.commit()
        conn.close()


    @staticmethod
    def pay_bill(card_id: int, amount: float, account_id: int, date: str = None):
        from services.transaction_service import TransactionService
        conn = get_db_connection()
        card_name = conn.execute("SELECT name FROM credit_cards WHERE id = ?", (card_id,)).fetchone()[0]
        
        # TRANSACTION DRIVEN: Record bill payment in main ledger
        # Type "transfer" ensures it doesnt double count as expense (already recorded at purchase)
        TransactionService.add_transaction(
            type="transfer",
            amount=amount,
            category="Credit Card Bill",
            date=date or datetime.now().strftime("%Y-%m-%d"),
            account_id=account_id,
            card_id=card_id,
            notes=f"Bill payment for {card_name}"
        )
        conn.close()


    @staticmethod
    def close_card(card_id: int, amount: float = 0, account_id: int = None):
        if amount > 0 and account_id:
            CreditCardService.pay_bill(card_id, amount, account_id)
            
        conn = get_db_connection()
        conn.execute("UPDATE credit_cards SET status = \"closed\" WHERE id = ?", (card_id,))
        conn.commit()
        conn.close()

