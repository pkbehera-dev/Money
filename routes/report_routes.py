from flask import Blueprint, render_template, request
from services.analytics_service import AnalyticsService
from database.connection import get_db_connection
import json

report_bp = Blueprint('report', __name__)

@report_bp.route('/reports')
def reports_page():
    # Force an update of summaries for fresh data
    AnalyticsService.refresh_summaries()
    
    range_val = request.args.get('range', 'monthly').lower()
    
    # Fetch precomputed analytics
    stats = AnalyticsService.get_quick_stats()
    behavior = AnalyticsService.get_behavior_analytics()
    insights = AnalyticsService.get_spending_insights()
    
    # Query database based on range switch
    conn = get_db_connection()
    trend_data = []
    category_data = []
    
    try:
        if range_val == 'weekly':
            # 1. Weekly trends
            rows = conn.execute("SELECT week as label, income, expense, savings, tx_count FROM weekly_summaries ORDER BY week DESC LIMIT 12").fetchall()
            trend_data = [
                {"label": r["label"], "income_total": float(r["income"] or 0), "expense_total": float(r["expense"] or 0), "savings": float(r["savings"] or 0), "tx_count": r["tx_count"]}
                for r in reversed(rows)
            ]
            # 2. Category distribution (summed over the last 12 weeks)
            category_totals = {}
            for r in rows:
                row = conn.execute("SELECT category_totals FROM weekly_summaries WHERE week = ?", (r["label"],)).fetchone()
                if row and row["category_totals"]:
                    try:
                        cats = json.loads(row["category_totals"])
                        for c, v in cats.items():
                            category_totals[c] = category_totals.get(c, 0.0) + float(v)
                    except Exception:
                        pass
            sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            category_data = [{"category": c[0], "total": float(c[1])} for c in sorted_cats]
            
        elif range_val == 'yearly':
            # 1. Yearly trends
            rows = conn.execute("SELECT year as label, income, expense, savings, tx_count FROM yearly_summaries ORDER BY year DESC LIMIT 10").fetchall()
            trend_data = [
                {"label": r["label"], "income_total": float(r["income"] or 0), "expense_total": float(r["expense"] or 0), "savings": float(r["savings"] or 0), "tx_count": r["tx_count"]}
                for r in reversed(rows)
            ]
            # 2. Category distribution (summed over the last year)
            category_totals = {}
            if rows:
                row = conn.execute("SELECT category_totals FROM yearly_summaries WHERE year = ?", (rows[0]["label"],)).fetchone()
                if row and row["category_totals"]:
                    try:
                        cats = json.loads(row["category_totals"])
                        for c, v in cats.items():
                            category_totals[c] = category_totals.get(c, 0.0) + float(v)
                    except Exception:
                        pass
            sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            category_data = [{"category": c[0], "total": float(c[1])} for c in sorted_cats]
            
        else: # 'monthly' (Default)
            rows = conn.execute("SELECT month as label, income, expense, savings, tx_count FROM monthly_summaries ORDER BY month DESC LIMIT 12").fetchall()
            trend_data = [
                {"label": r["label"], "income_total": float(r["income"] or 0), "expense_total": float(r["expense"] or 0), "savings": float(r["savings"] or 0), "tx_count": r["tx_count"]}
                for r in reversed(rows)
            ]
            # 2. Category distribution (last month)
            if rows:
                row = conn.execute("SELECT category_totals FROM monthly_summaries WHERE month = ?", (rows[0]["label"],)).fetchone()
                if row and row["category_totals"]:
                    try:
                        cats = json.loads(row["category_totals"])
                        category_data = [{"category": c, "total": float(t)} for c, t in cats.items()]
                        category_data = sorted(category_data, key=lambda x: x["total"], reverse=True)
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error compiling reports page data: {e}")
    finally:
        conn.close()
        
    return render_template('reports.html', 
                           stats=stats,
                           trend_data=trend_data,
                           category_data=category_data,
                           behavior=behavior,
                           insights=insights,
                           current_range=range_val,
                           partial=request.args.get('partial'))
