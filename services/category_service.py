from database.connection import get_db_connection

class CategoryService:
    @staticmethod
    def get_all_categories(tx_type=None):
        conn = get_db_connection()
        query = "SELECT * FROM categories"
        params = []
        if tx_type:
            query += " WHERE type = ?"
            params.append(tx_type)
        query += " ORDER BY name ASC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add_category(name, tx_type):
        conn = get_db_connection()
        conn.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, tx_type))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_category(cat_id):
        conn = get_db_connection()
        conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        conn.close()
