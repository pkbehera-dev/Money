from flask import Blueprint, render_template, request
from services.analytics_service import AnalyticsService

report_bp = Blueprint('report', __name__)

@report_bp.route('/reports')
def reports_page():
    # Force an update of summaries for fresh data (In production, this would be a background task)
    AnalyticsService.update_summaries()
    
    # Fetch precomputed analytics
    stats = AnalyticsService.get_quick_stats()
    trend_data = AnalyticsService.get_monthly_trends()
    category_data = AnalyticsService.get_category_distribution()
    behavior = AnalyticsService.get_behavior_analytics()
    insights = AnalyticsService.get_spending_insights()
    
    return render_template('reports.html', 
                           stats=stats,
                           trend_data=trend_data,
                           category_data=category_data,
                           behavior=behavior,
                           insights=insights,
                           partial=request.args.get('partial'))
