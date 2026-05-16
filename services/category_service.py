from database.connection import get_db_connection

class CategoryService:
    @staticmethod
    def get_all_categories(type_filter=None):
        conn = get_db_connection()
        if type_filter:
            rows = conn.execute("SELECT * FROM categories WHERE type = ? AND deleted_at IS NULL ORDER BY name ASC", (type_filter,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM categories WHERE deleted_at IS NULL ORDER BY name ASC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add_category(name, category_type):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, category_type))
            conn.commit()
            return cursor.lastrowid
        except:
            return None
        finally:
            conn.close()

    @staticmethod
    def delete_category(category_id):
        from datetime import datetime
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE categories SET deleted_at = ? WHERE id = ?", (now, category_id))
        conn.commit()
        conn.close()
