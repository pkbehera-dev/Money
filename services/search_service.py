from database.connection import get_db_connection

class SearchService:
    @staticmethod
    def get_search_index():
        """Fetches all searchable entities for client-side indexing."""
        conn = get_db_connection()
        index = {
            "transactions": [],
            "accounts": [],
            "people": [],
            "loans": [],
            "categories": []
        }
        
        # 1. Transactions (Last 500 for speed)
        txs = conn.execute("""
            SELECT t.id, t.amount, t.category, t.date, t.type, t.notes, t.tags, a.name as account_name 
            FROM transactions t 
            LEFT JOIN accounts a ON t.account_id = a.id 
            WHERE t.deleted_at IS NULL
            ORDER BY t.date DESC LIMIT 500
        """).fetchall()
        index["transactions"] = [dict(tx) for tx in txs]
        
        # 2. Accounts & Cards
        accs = conn.execute("SELECT id, name, type, balance FROM accounts").fetchall()
        index["accounts"] = [dict(acc) for acc in accs]
        
        cards = conn.execute("SELECT id, name, 'Credit Card' as type, (card_limit - outstanding) as balance FROM credit_cards").fetchall()
        index["accounts"].extend([dict(c) for c in cards])
        
        # 3. People
        people = conn.execute("SELECT id, person_name, SUM(total_amount - paid_amount) as balance FROM people_ledger WHERE deleted_at IS NULL GROUP BY person_name").fetchall()
        index["people"] = [dict(p) for p in people]
        
        # 4. Loans
        loans = conn.execute("SELECT id, name, (total_to_pay - paid_amount) as remaining FROM loans WHERE status = 'active' AND deleted_at IS NULL").fetchall()
        index["loans"] = [dict(l) for l in loans]

        # 5. Categories
        cats = conn.execute("SELECT DISTINCT name, type FROM categories WHERE deleted_at IS NULL").fetchall()
        index["categories"] = [dict(c) for c in cats]

        conn.close()
        return index

    @staticmethod
    def global_search(query):
        # Legacy fallback if needed, but we'll prioritize the new local index
        pass
