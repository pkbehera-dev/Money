from database.connection import get_db_connection
from datetime import datetime

class AssetService:
    @staticmethod
    def get_all_assets(filters=None):
        conn = get_db_connection()
        query = "SELECT * FROM assets WHERE deleted_at IS NULL ORDER BY category, name"
        rows = conn.execute(query).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_asset_by_id(asset_id):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM assets WHERE id = ? AND deleted_at IS NULL", (asset_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create_asset(name, category, purchase_value, current_value, purchase_date, notes=None, depreciation_enabled=0):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO assets (name, category, purchase_value, current_value, purchase_date, notes, depreciation_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, category, purchase_value, current_value, purchase_date, notes, depreciation_enabled))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    @staticmethod
    def update_asset(asset_id, **kwargs):
        conn = get_db_connection()
        fields = []
        params = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            params.append(value)
        params.append(asset_id)
        
        conn.execute(f"UPDATE assets SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    @staticmethod
    def delete_asset(asset_id):
        conn = get_db_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE assets SET deleted_at = ? WHERE id = ?", (now, asset_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_total_asset_value():
        conn = get_db_connection()
        row = conn.execute("SELECT SUM(current_value) FROM assets WHERE deleted_at IS NULL").fetchone()
        conn.close()
        return row[0] or 0.0

    @staticmethod
    def get_asset_stats():
        conn = get_db_connection()
        stats = conn.execute('''
            SELECT 
                COALESCE(SUM(purchase_value), 0) as total_purchase,
                COALESCE(SUM(current_value), 0) as total_current,
                COUNT(*) as count
            FROM assets
            WHERE deleted_at IS NULL
        ''').fetchone()
        conn.close()
        
        res = {
            'total_purchase': float(stats['total_purchase'] or 0),
            'total_current': float(stats['total_current'] or 0),
            'count': stats['count'] or 0
        }
        res['gain_loss'] = res['total_current'] - res['total_purchase']
        res['growth_pct'] = (res['gain_loss'] / res['total_purchase'] * 100) if res['total_purchase'] > 0 else 0
        return res
