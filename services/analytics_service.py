import sqlite3
import json
from database.connection import get_db_connection
from datetime import datetime, timedelta

class AnalyticsService:
    @staticmethod
    def refresh_summaries():
        """Recalculates daily, weekly, monthly, and yearly summaries for the active 12-month window."""
        conn = get_db_connection()
        try:
            # 1. Calculate active threshold date (12 months ago)
            today = datetime.today().date()
            active_threshold = (today - timedelta(days=365)).isoformat()
            active_month_threshold = active_threshold[:7]
            active_year_threshold = active_threshold[:4]
            
            # 2. Clear only the active 12-month window summaries to preserve historical precomputed summaries
            conn.execute("DELETE FROM daily_summaries WHERE date >= ?", (active_threshold,))
            conn.execute("DELETE FROM weekly_summaries WHERE start_date >= ?", (active_threshold,))
            conn.execute("DELETE FROM monthly_summaries WHERE month >= ?", (active_month_threshold,))
            conn.execute("DELETE FROM yearly_summaries WHERE year >= ?", (active_year_threshold,))
            conn.commit()
            
            # 3. Fetch active raw transactions (date >= active_threshold)
            query = """
                SELECT date, type, category, SUM(amount) as total, COUNT(*) as cnt
                FROM transactions
                WHERE date >= ? AND deleted_at IS NULL
                AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
                GROUP BY date, type, category
                ORDER BY date ASC
            """
            rows = conn.execute(query, (active_threshold,)).fetchall()
            
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
            
            # Anchor calculations based on today's live assets/liabilities
            from services.net_worth_service import NetWorthService
            nw_today = 0.0
            try:
                nw_today = float(NetWorthService.calculate_net_worth()[0])
            except Exception:
                pass
                
            score_today = 80
            try:
                row_health = conn.execute("SELECT score FROM health_history ORDER BY date DESC LIMIT 1").fetchone()
                if row_health:
                    score_today = int(row_health['score'])
            except Exception:
                pass
            
            # Calculate savings and net worth walkback for active window
            total_active_savings = 0.0
            for d_str, data in daily_data.items():
                total_active_savings += (data['income'] - data['expense'])
                
            nw_current = nw_today - total_active_savings
            
            # Retrieve health history cache for active period
            health_rows = conn.execute("SELECT date, score FROM health_history WHERE date >= ?", (active_threshold,)).fetchall()
            health_cache = {h['date']: h['score'] for h in health_rows}
            
            # Pre-aggregate active credit usage
            credit_rows = conn.execute("""
                SELECT date, SUM(amount) as total
                FROM transactions
                WHERE card_id IS NOT NULL AND type='expense' AND deleted_at IS NULL AND date >= ?
                AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
                GROUP BY date
            """, (active_threshold,)).fetchall()
            credit_cache = {}
            for cr in credit_rows:
                d_key = cr['date'][:10]
                credit_cache[d_key] = credit_cache.get(d_key, 0.0) + float(cr['total'])
            
            daily_records = []
            curr_date = datetime.strptime(active_threshold, "%Y-%m-%d").date()
            
            while curr_date <= today:
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
                    1
                ))
                curr_date += timedelta(days=1)
                
            # Insert/Replace active daily summaries
            conn.executemany("""
                INSERT OR REPLACE INTO daily_summaries 
                (date, income, expense, savings, net_worth, financial_score, credit_usage, category_totals, tx_count, summary_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, daily_records)
            
            # Aggregate Active Weekly Summaries
            weekly_data = {}
            for r in daily_records:
                d_obj = datetime.strptime(r[0], "%Y-%m-%d").date()
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
                w['nw'] = r[4]
                w['score'] = r[5]
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
            
            # Aggregate Active Monthly Summaries
            monthly_data = {}
            for r in daily_records:
                month_str = r[0][:7]
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
            
            # Aggregate Active Yearly Summaries
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
        except Exception as e:
            print(f"Error during refresh_summaries: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
            
        # 4. Trigger Checks
        try:
            from services.notification_service import NotificationService
            NotificationService.check_all_triggers()
        except Exception as e:
            print(f"Periodic check failed: {e}")

    @staticmethod
    def archive_old_data():
        """Retention Strategy: Delegate to HistoricalSummaryEngine."""
        from services.historical_summary_service import HistoricalSummaryEngine
        return HistoricalSummaryEngine.archive_older_transactions(12)

    @staticmethod
    def get_monthly_trends():
        conn = get_db_connection()
        rows = conn.execute("SELECT month, income as income_total, expense as expense_total, savings, credit_usage, tx_count FROM monthly_summaries ORDER BY month DESC LIMIT 12").fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    @staticmethod
    def get_category_distribution(month=None):
        if not month:
            month = datetime.now().strftime('%Y-%m')
        conn = get_db_connection()
        row = conn.execute("SELECT category_totals FROM monthly_summaries WHERE month = ?", (month,)).fetchone()
        conn.close()
        if row and row['category_totals']:
            try:
                cats = json.loads(row['category_totals'])
                res = [{'category': c, 'total': float(t)} for c, t in cats.items()]
                return sorted(res, key=lambda x: x['total'], reverse=True)
            except Exception:
                pass
        return []

    @staticmethod
    def get_quick_stats():
        conn = get_db_connection()
        this_month = datetime.now().strftime('%Y-%m')
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        # Monthly performance (with aliasing for strict backwards compatibility)
        row = conn.execute("SELECT income as income_total, expense as expense_total, savings, credit_usage, tx_count FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        prev_row = conn.execute("SELECT income as income_total, expense as expense_total, savings, credit_usage, tx_count FROM monthly_summaries WHERE month = ?", (last_month,)).fetchone()
        
        # Account Balances (Liquid)
        liquid = conn.execute("SELECT SUM(balance) FROM accounts WHERE deleted_at IS NULL").fetchone()[0] or 0
        
        # Non-Liquid Assets (Property, Gold, etc.)
        from services.asset_service import AssetService
        non_liquid = AssetService.get_total_asset_value()
        
        # People Ledger (Lent/Borrowed)
        lent_total = conn.execute("SELECT SUM(total_amount - paid_amount) FROM people_ledger WHERE type = 'lent' AND deleted_at IS NULL").fetchone()[0] or 0
        borrowed_total = conn.execute("SELECT SUM(total_amount - paid_amount) FROM people_ledger WHERE type = 'borrowed' AND deleted_at IS NULL").fetchone()[0] or 0
        
        # Debt calculation
        loans_total = conn.execute("SELECT SUM(total_to_pay) FROM loans WHERE status = 'active' AND deleted_at IS NULL").fetchone()[0] or 0
        loan_payments = conn.execute("SELECT SUM(amount) FROM loan_payments WHERE deleted_at IS NULL").fetchone()[0] or 0
        loan_debt = loans_total - loan_payments
        
        card_purchases = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'expense' AND deleted_at IS NULL").fetchone()[0] or 0
        card_withdrawals = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'transfer' AND account_id IS NULL AND to_account_id IS NOT NULL AND deleted_at IS NULL").fetchone()[0] or 0
        card_payments = conn.execute("SELECT SUM(amount) FROM transactions WHERE card_id IS NOT NULL AND type = 'transfer' AND account_id IS NOT NULL AND deleted_at IS NULL").fetchone()[0] or 0
        card_debt = (card_purchases + card_withdrawals) - card_payments

        # Reserved Goals
        goal_total = conn.execute("SELECT SUM(current_amount) FROM goals WHERE deleted_at IS NULL").fetchone()[0] or 0

        total_assets = liquid + non_liquid + lent_total + goal_total
        total_liabilities = loan_debt + card_debt + borrowed_total
        net_worth = total_assets - total_liabilities
        
        # Trends
        income_this = row['income_total'] if row else 0
        income_prev = prev_row['income_total'] if prev_row else 0
        income_change = ((income_this - income_prev) / income_prev * 100) if income_prev > 0 else 0
        
        expense_this = row['expense_total'] if row else 0
        expense_prev = prev_row['expense_total'] if prev_row else 0
        expense_change = ((expense_this - expense_prev) / expense_prev * 100) if expense_prev > 0 else 0
        
        # Chart Data: Trends (6 Months)
        trend_rows = conn.execute("SELECT month, income as income_total, expense as expense_total FROM monthly_summaries ORDER BY month DESC LIMIT 6").fetchall()
        trend_rows = reversed(trend_rows)
        chart_trends = {"labels": [], "income": [], "expense": []}
        for tr in trend_rows:
            chart_trends["labels"].append(tr['month'])
            chart_trends["income"].append(float(tr['income_total']))
            chart_trends["expense"].append(float(tr['expense_total']))
            
        # Chart Data: Category (This Month)
        chart_category = {"labels": [], "data": []}
        cats_dist = AnalyticsService.get_category_distribution(this_month)
        for cr in cats_dist[:10]:
            chart_category["labels"].append(cr['category'])
            chart_category["data"].append(float(cr['total']))

        conn.close()
        
        return {
            "net_worth_stats": {
                "total": float(net_worth),
                "assets": float(total_assets),
                "liabilities": float(total_liabilities),
                "change_pct": income_change - expense_change
            },
            "income_stats": {
                "total": float(income_this),
                "change_pct": income_change
            },
            "expense_stats": {
                "total": float(expense_this),
                "change_pct": expense_change
            },
            "savings_stats": {
                "total": float(income_this - expense_this),
                "savings_rate": (income_this - expense_this) / income_this * 100 if income_this > 0 else 0
            },
            "net_savings": float(income_this - expense_this),
            "net_worth": float(net_worth),
            "income_total": float(income_this),
            "expense_total": float(expense_this),
            "chart_trends": chart_trends,
            "chart_category": chart_category
        }
        
    @staticmethod
    def get_behavior_analytics():
        conn = get_db_connection()
        weekday_avg = conn.execute("SELECT AVG(amount) FROM transactions WHERE type='expense' AND deleted_at IS NULL AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration') AND strftime('%w', date) BETWEEN '1' AND '5'").fetchone()[0] or 0
        weekend_avg = conn.execute("SELECT AVG(amount) FROM transactions WHERE type='expense' AND deleted_at IS NULL AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration') AND strftime('%w', date) IN ('0', '6')").fetchone()[0] or 0
        
        active_day_idx = conn.execute("SELECT strftime('%w', date) as day, SUM(amount) as total FROM transactions WHERE type='expense' AND deleted_at IS NULL AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration') GROUP BY day ORDER BY total DESC LIMIT 1").fetchone()
        
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        active_day = days[int(active_day_idx[0])] if active_day_idx and active_day_idx[0] is not None else "None"
        
        diff_pct = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0
        conn.close()
        return {"weekend_diff": diff_pct, "active_day": active_day, "avg_daily": (weekday_avg + weekend_avg) / 2}

    @staticmethod
    def get_spending_insights():
        conn = get_db_connection()
        insights = []
        this_month = datetime.now().strftime('%Y-%m')
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        m1 = conn.execute("SELECT expense, income FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        m2 = conn.execute("SELECT expense, income FROM monthly_summaries WHERE month = ?", (last_month,)).fetchone()
        
        this_month_expense = 0.0
        this_month_income = 0.0
        if m1:
            this_month_expense = float(m1['expense'] or 0.0)
            this_month_income = float(m1['income'] or 0.0)
            
        last_month_expense = 0.0
        last_month_income = 0.0
        if m2:
            last_month_expense = float(m2['expense'] or 0.0)
            last_month_income = float(m2['income'] or 0.0)

        # Helper function for next due date
        def get_next_due_date_for_day(day):
            import calendar
            t = datetime.now()
            _, max_days = calendar.monthrange(t.year, t.month)
            due_this_month = datetime(t.year, t.month, min(day, max_days))
            if due_this_month.date() < t.date():
                # Next month
                ny = t.year if t.month < 12 else t.year + 1
                nm = t.month + 1 if t.month < 12 else 1
                _, max_days_next = calendar.monthrange(ny, nm)
                return datetime(ny, nm, min(day, max_days_next))
            return due_this_month

        # 1. Spending Trend (MoM)
        if last_month_expense > 0:
            change = ((this_month_expense - last_month_expense) / last_month_expense) * 100
            if change > 10: 
                insights.append({"type": "warning", "icon": "ph-trend-up", "text": f"Spending rose {change:.1f}% vs last month."})
            elif change < -5: 
                insights.append({"type": "success", "icon": "ph-trend-down", "text": f"Spending down {abs(change):.1f}% vs last month."})
            else:
                insights.append({"type": "success", "icon": "ph-trend-down", "text": "Spending is stable compared to last month."})
        else:
            if this_month_expense > 0:
                insights.append({"type": "tip", "icon": "ph-trend-up", "text": f"Total spending this month is ₹{this_month_expense:.0f}. MoM trend will be active next month."})

        # 2. Spending Category Spikes (threshold: max of 500 or 20% of total monthly spending)
        row_month = conn.execute("SELECT category_totals FROM monthly_summaries WHERE month = ?", (this_month,)).fetchone()
        if row_month and row_month['category_totals']:
            try:
                cats = json.loads(row_month['category_totals'])
                threshold = max(500.0, this_month_expense * 0.20)
                spikes = sorted([(c, float(t)) for c, t in cats.items() if float(t) > threshold], key=lambda x: x[1], reverse=True)[:2]
                for s in spikes: 
                    cat_name = s[0]
                    cat_total = s[1]
                    # Find the largest transaction in this category to see if it dominates
                    largest_cat_tx = conn.execute("""
                        SELECT amount 
                        FROM transactions 
                        WHERE type = 'expense' 
                        AND category = ? 
                        AND date LIKE ? 
                        AND deleted_at IS NULL
                        ORDER BY amount DESC 
                        LIMIT 1
                    """, (cat_name, f"{this_month}%")).fetchone()
                    if largest_cat_tx:
                        largest_cat_tx_amt = float(largest_cat_tx['amount'])
                        # Suppress category spikes where a single transaction dominates (>= 70% of the total).
                        # This justifies their separate creation reasons:
                        # - Largest Single Expense focuses on one major expense.
                        # - Spending Category Spikes focuses on cumulative/behavioral trends.
                        if largest_cat_tx_amt >= cat_total * 0.70:
                            continue
                    insights.append({"type": "tip", "icon": "ph-lightbulb", "text": f"{s[0]} is a top expense (₹{s[1]:.0f})."})
            except Exception:
                pass

        # 3. Daily Spending Pace & Projection
        import calendar
        today = datetime.now()
        days_elapsed = today.day
        _, total_days = calendar.monthrange(today.year, today.month)
        if this_month_expense > 0:
            daily_pace = this_month_expense / days_elapsed
            projected_spending = daily_pace * total_days
            
            if this_month_income > 0 and projected_spending > this_month_income:
                insights.append({
                    "type": "warning", 
                    "icon": "ph-calendar-x", 
                    "text": f"At your current pace (₹{daily_pace:.0f}/day), you are projected to spend ₹{projected_spending:.0f}, which exceeds your monthly income."
                })
            elif last_month_expense > 0 and projected_spending > last_month_expense * 1.15:
                insights.append({
                    "type": "tip", 
                    "icon": "ph-chart-line-up", 
                    "text": f"Current pace (₹{daily_pace:.0f}/day) projects to ₹{projected_spending:.0f}, higher than last month's ₹{last_month_expense:.0f}."
                })

        # 4. Largest Single Expense
        largest_tx = conn.execute("""
            SELECT category, amount, notes 
            FROM transactions 
            WHERE type = 'expense' 
            AND date LIKE ? 
            AND deleted_at IS NULL 
            AND category NOT IN ('Credit Card Entry', 'Initial Balance', 'Loan Principal Migration')
            ORDER BY amount DESC 
            LIMIT 1
        """, (f"{this_month}%",)).fetchone()
        if largest_tx:
            desc = largest_tx['notes'] if (largest_tx['notes'] and largest_tx['notes'].strip()) else largest_tx['category']
            if len(desc) > 30:
                desc = desc[:27] + "..."
            insights.append({
                "type": "tip", 
                "icon": "ph-shopping-cart", 
                "text": f"Largest single expense: ₹{largest_tx['amount']:.0f} for '{desc}'."
            })

        # 5. Credit Card Utilization Warning
        try:
            from services.credit_card_service import CreditCardService
            cards = CreditCardService.get_all_cards()
            for card in cards:
                if card.get('status') == 'active' and card.get('card_limit', 0) > 0:
                    usage = card['usage_pct']
                    if usage >= 80:
                        insights.append({
                            "type": "warning",
                            "icon": "ph-warning-circle",
                            "text": f"Critical limit: {card['name']} utilization is at {usage:.1f}% (₹{card['outstanding']:.0f}/₹{card['card_limit']:.0f})."
                        })
                    elif usage >= 50:
                        insights.append({
                            "type": "tip",
                            "icon": "ph-info",
                            "text": f"High usage: {card['name']} utilization is at {usage:.1f}%."
                        })
        except Exception as e:
            print(f"Error calculating card utilization: {e}")

        # 6. Upcoming Due Dates (within 7 days)
        # Credit Card dues
        try:
            for card in cards:
                if card.get('status') == 'active' and card.get('outstanding', 0) > 0 and card.get('due_date'):
                    due_day = card['due_date']
                    target_due = get_next_due_date_for_day(due_day)
                    days_until = (target_due.date() - today.date()).days
                    if 0 <= days_until <= 7:
                        insights.append({
                            "type": "warning",
                            "icon": "ph-credit-card",
                            "text": f"Upcoming bill: {card['name']} payment of ₹{card['outstanding']:.0f} is due in {days_until} days ({target_due.strftime('%b %d')})."
                        })
        except Exception as e:
            print(f"Error calculating card due dates: {e}")

        # Loan dues
        try:
            loans_rows = conn.execute("SELECT id, name, total_to_pay, paid_amount, tenure, due_date FROM loans WHERE status='active' AND deleted_at IS NULL").fetchall()
            for l in loans_rows:
                remaining = l['total_to_pay'] - l['paid_amount']
                if remaining > 0 and l['due_date']:
                    due_day = l['due_date']
                    target_due = get_next_due_date_for_day(due_day)
                    days_until = (target_due.date() - today.date()).days
                    if 0 <= days_until <= 7:
                        emi = l['total_to_pay'] / l['tenure'] if l['tenure'] > 0 else remaining
                        insights.append({
                            "type": "warning",
                            "icon": "ph-calendar-warning",
                            "text": f"Upcoming loan: '{l['name']}' EMI (approx ₹{emi:.0f}) is due in {days_until} days ({target_due.strftime('%b %d')})."
                        })
        except Exception as e:
            print(f"Error calculating loan due dates: {e}")

        # 7. Savings Rate Insight
        if this_month_income > 0:
            savings = this_month_income - this_month_expense
            savings_rate = (savings / this_month_income) * 100
            if savings_rate > 40:
                insights.append({
                    "type": "success",
                    "icon": "ph-piggy-bank",
                    "text": f"Excellent! Your savings rate is {savings_rate:.1f}% this month, well above the 40% goal."
                })
            elif savings_rate < 20:
                insights.append({
                    "type": "warning",
                    "icon": "ph-trend-down",
                    "text": f"Your savings rate is {savings_rate:.1f}% this month. Consider reducing non-essential expenses to hit 20%."
                })

        # 8. Budget Thresholds
        try:
            from services.budget_service import BudgetService
            budgets = BudgetService.get_all_budgets()
            for b in budgets:
                if b.get('status') == 'active' and b.get('progress', 0) > 80:
                    insights.append({
                        "type": "warning" if b['progress'] >= 100 else "tip", 
                        "icon": "ph-warning-circle" if b['progress'] >= 100 else "ph-info",
                        "text": f"Budget '{b['name']}' is {b['progress']:.1f}% used."
                    })
        except Exception as e:
            print(f"Error reading budget thresholds: {e}")

        # 9. Goal Velocity Insights
        try:
            from services.goal_service import GoalService
            goals = GoalService.get_all_goals()
            for g in goals:
                if g['status'] == 'active':
                    if g['tracking_text'] == 'Behind':
                        insights.append({"type": "warning", "icon": "ph-warning", "text": f"Goal '{g['name']}' is behind schedule. Consider increasing contributions."})
                    elif g['tracking_text'] == 'Ahead':
                        insights.append({"type": "success", "icon": "ph-rocket-launch", "text": f"You're ahead of schedule on '{g['name']}'! Excellent velocity."})
        except Exception as e:
            print(f"Error reading goal velocity: {e}")

        # 10. Net Worth Insight
        try:
            from services.net_worth_service import NetWorthService
            nw_change = NetWorthService.get_monthly_change()
            if nw_change > 2:
                insights.append({"type": "success", "icon": "ph-chart-line-up", "text": f"Your net worth grew by {nw_change:.1f}% this month. Great job!"})
            elif nw_change < -2:
                insights.append({"type": "warning", "icon": "ph-chart-line-down", "text": f"Net worth decreased by {abs(nw_change):.1f}%. Check your latest liabilities."})
        except Exception as e:
            print(f"Error checking net worth monthly change: {e}")

        # 11. General Tips (Fallback)
        if not insights: 
            insights.append({"type": "tip", "icon": "ph-sparkle", "text": "Keep tracking your daily expenses to get deeper insights."})
        
        conn.close()
        return insights
