import json
import datetime
import sqlite3
from database.connection import get_db_connection, DB_PATH

class HistoricalSummaryEngine:
    @staticmethod
    def archive_older_transactions(limit_months=12):
        """
        Retention Strategy:
        0-12 months: Keep complete transaction logs.
        Older than 12 months: Archive and delete from transactions.
        """
        conn = get_db_connection()
        try:
            today = datetime.date.today()
            # 12 months threshold date
            threshold_date = (today - datetime.timedelta(days=int(limit_months * 30.5))).isoformat()
            
            # Step 1: Ensure daily summaries exist for the historical transactions before they are deleted
            # We run rebuild_all_summaries to guarantee everything is summarized
            HistoricalSummaryEngine.rebuild_all_summaries()
            
            # Step 2: Copy raw transactions to transaction_archive
            conn.execute("""
                INSERT OR IGNORE INTO transaction_archive (id, account_id, amount, type, category, date, notes, created_at)
                SELECT id, account_id, amount, type, category, date, notes, datetime('now')
                FROM transactions
                WHERE date < ? AND deleted_at IS NULL
            """, (threshold_date,))
            
            # Step 3: Delete raw transactions from the primary table
            conn.execute("DELETE FROM transactions WHERE date < ? AND deleted_at IS NULL", (threshold_date,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error during archival: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def rebuild_all_summaries():
        """
        HistoricalRebuildEngine:
        Rebuilds all summaries from BOTH raw transactions and transaction_archive.
        Useful for corruption, migrations, and schema updates.
        """
        # Retrieve latest net worth and health score using direct read-only queries to prevent nested locking conflicts
        from services.net_worth_service import NetWorthService
        nw_today = 0.0
        try:
            nw_today = float(NetWorthService.calculate_net_worth()[0])
        except Exception:
            pass
            
        score_today = 80
        conn_temp = get_db_connection()
        try:
            row_health = conn_temp.execute("SELECT score FROM health_history ORDER BY date DESC LIMIT 1").fetchone()
            if row_health:
                score_today = int(row_health['score'])
        except Exception:
            pass
        finally:
            conn_temp.close()

        conn = get_db_connection()
        try:
            # Clear existing summaries to perform a clean rebuild
            conn.execute("DELETE FROM daily_summaries")
            conn.execute("DELETE FROM weekly_summaries")
            conn.execute("DELETE FROM monthly_summaries")
            conn.execute("DELETE FROM yearly_summaries")
            conn.commit()
            
            # 1. Fetch min and max dates across both raw and archived transactions
            row = conn.execute("""
                SELECT MIN(date), MAX(date) FROM (
                    SELECT date FROM transactions WHERE deleted_at IS NULL
                    UNION
                    SELECT date FROM transaction_archive
                )
            """).fetchone()
            
            if not row or not row[0]:
                return True # No transactions to rebuild summaries for
                
            min_date_str = row[0][:10]
            min_date = datetime.datetime.strptime(min_date_str, "%Y-%m-%d").date()
            max_date = datetime.date.today()
            
            # 3. Retrieve and aggregate all transactions by day from BOTH tables
            query = """
                SELECT date, type, category, SUM(amount) as total, COUNT(*) as cnt
                FROM (
                    SELECT date, type, category, amount FROM transactions WHERE deleted_at IS NULL
                    UNION ALL
                    SELECT date, type, category, amount FROM transaction_archive
                )
                GROUP BY date, type, category
                ORDER BY date ASC
            """
            rows = conn.execute(query).fetchall()
            
            # Group rows by date
            daily_data = {}
            for r in rows:
                d_str = r['date'][:10]
                if d_str not in daily_data:
                    daily_data[d_str] = {'income': 0.0, 'expense': 0.0, 'cats': {}, 'cnt': 0}
                
                daily_data[d_str]['cnt'] += r['cnt']
                
                if r['type'] == 'income':
                    daily_data[d_str]['income'] += float(r['total'])
                elif r['type'] == 'expense':
                    daily_data[d_str]['expense'] += float(r['total'])
                    cat = r['category'] or 'Uncategorized'
                    daily_data[d_str]['cats'][cat] = daily_data[d_str]['cats'].get(cat, 0.0) + float(r['total'])
            
            # 4. Perform backwards net worth calculations
            total_savings = 0.0
            for d_str, data in daily_data.items():
                total_savings += (data['income'] - data['expense'])
                
            nw_current = nw_today - total_savings # Anchor value at min_date
            
            # Retrieve cached past health scores
            health_rows = conn.execute("SELECT date, score FROM health_history").fetchall()
            health_cache = {h['date']: h['score'] for h in health_rows}
            
            # Pre-aggregate credit usage by date in a single fast query to avoid nested loops and lock contention
            credit_rows = conn.execute("""
                SELECT date, SUM(amount) as total
                FROM (
                    SELECT date, amount FROM transactions WHERE card_id IS NOT NULL AND type='expense' AND deleted_at IS NULL
                    UNION ALL
                    SELECT date, amount FROM transaction_archive WHERE type='expense' AND account_id IS NULL
                )
                GROUP BY date
            """).fetchall()
            credit_cache = {}
            for cr in credit_rows:
                d_key = cr['date'][:10]
                credit_cache[d_key] = credit_cache.get(d_key, 0.0) + float(cr['total'])
            
            daily_records = []
            curr_date = min_date
            
            while curr_date <= max_date:
                d_str = curr_date.isoformat()
                data = daily_data.get(d_str, {'income': 0.0, 'expense': 0.0, 'cats': {}, 'cnt': 0})
                
                nw_current += (data['income'] - data['expense'])
                score = health_cache.get(d_str, score_today)
                credit_val = credit_cache.get(d_str, 0.0)
                
                daily_records.append((
                    d_str,
                    data['income'],
                    data['expense'],
                    data['income'] - data['expense'],
                    nw_current,
                    score,
                    credit_val,
                    json.dumps(data['cats']),
                    data['cnt'],
                    1 # summary_version
                ))
                
                curr_date += datetime.timedelta(days=1)
                
            # Populate daily_summaries
            conn.executemany("""
                INSERT OR REPLACE INTO daily_summaries 
                (date, income, expense, savings, net_worth, financial_score, credit_usage, category_totals, tx_count, summary_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, daily_records)
            
            conn.commit()
            
            # 5. Populate Weekly Summaries from daily summaries
            weekly_data = {}
            for r in daily_records:
                d_obj = datetime.datetime.strptime(r[0], "%Y-%m-%d").date()
                year, week, weekday = d_obj.isocalendar()
                week_str = f"{year}-W{week:02d}"
                
                if week_str not in weekly_data:
                    weekly_data[week_str] = {
                        'start': r[0], 'end': r[0],
                        'income': 0.0, 'expense': 0.0, 'savings': 0.0,
                        'nw': r[4], 'score': r[5], 'credit': 0.0,
                        'cats': {}, 'cnt': 0
                    }
                w = weekly_data[week_str]
                if r[0] < w['start']: w['start'] = r[0]
                if r[0] > w['end']: w['end'] = r[0]
                w['income'] += r[1]
                w['expense'] += r[2]
                w['savings'] += r[3]
                w['nw'] = r[4] # Latest net worth of week
                w['score'] = r[5] # Latest score of week
                w['credit'] += r[6]
                w['cnt'] += r[8]
                
                daily_cats = json.loads(r[7])
                for c, v in daily_cats.items():
                    w['cats'][c] = w['cats'].get(c, 0.0) + v
                    
            weekly_records = []
            for wk, w in weekly_data.items():
                weekly_records.append((
                    wk, w['start'], w['end'],
                    w['income'], w['expense'], w['savings'],
                    w['nw'], w['score'], w['credit'],
                    json.dumps(w['cats']), w['cnt'], 1
                ))
            conn.executemany("""
                INSERT OR REPLACE INTO weekly_summaries 
                (week, start_date, end_date, income, expense, savings, net_worth, financial_score, credit_usage, category_totals, tx_count, summary_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, weekly_records)
            
            # 6. Populate Monthly Summaries from daily summaries
            monthly_data = {}
            for r in daily_records:
                month_str = r[0][:7] # YYYY-MM
                if month_str not in monthly_data:
                    monthly_data[month_str] = {
                        'income': 0.0, 'expense': 0.0, 'savings': 0.0,
                        'nw': r[4], 'score': r[5], 'credit': 0.0,
                        'cats': {}, 'cnt': 0
                    }
                m = monthly_data[month_str]
                m['income'] += r[1]
                m['expense'] += r[2]
                m['savings'] += r[3]
                m['nw'] = r[4]
                m['score'] = r[5]
                m['credit'] += r[6]
                m['cnt'] += r[8]
                
                daily_cats = json.loads(r[7])
                for c, v in daily_cats.items():
                    m['cats'][c] = m['cats'].get(c, 0.0) + v
                    
            monthly_records = []
            for mn, m in monthly_data.items():
                monthly_records.append((
                    mn, m['income'], m['expense'], m['savings'],
                    m['nw'], m['score'], m['credit'],
                    json.dumps(m['cats']), m['cnt'], 1
                ))
            conn.executemany("""
                INSERT OR REPLACE INTO monthly_summaries 
                (month, income, expense, savings, net_worth, financial_score, credit_usage, category_totals, tx_count, summary_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, monthly_records)
            
            # 7. Populate Yearly Summaries from daily summaries
            yearly_data = {}
            for r in daily_records:
                year_str = r[0][:4]
                if year_str not in yearly_data:
                    yearly_data[year_str] = {
                        'income': 0.0, 'expense': 0.0, 'savings': 0.0,
                        'nw': r[4], 'score': r[5], 'credit': 0.0,
                        'cats': {}, 'cnt': 0
                    }
                y = yearly_data[year_str]
                y['income'] += r[1]
                y['expense'] += r[2]
                y['savings'] += r[3]
                y['nw'] = r[4]
                y['score'] = r[5]
                y['credit'] += r[6]
                y['cnt'] += r[8]
                
                daily_cats = json.loads(r[7])
                for c, v in daily_cats.items():
                    y['cats'][c] = y['cats'].get(c, 0.0) + v
                    
            yearly_records = []
            for yr, y in yearly_data.items():
                yearly_records.append((
                    yr, y['income'], y['expense'], y['savings'],
                    y['nw'], y['score'], y['credit'],
                    json.dumps(y['cats']), y['cnt'], 1
                ))
            conn.executemany("""
                INSERT OR REPLACE INTO yearly_summaries 
                (year, income, expense, savings, net_worth, financial_score, credit_usage, category_totals, tx_count, summary_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, yearly_records)
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error rebuilding summaries: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()
