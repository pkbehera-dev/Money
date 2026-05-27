from flask import Blueprint, render_template, request, redirect, url_for, send_file
import shutil
import os
from database.connection import DB_PATH

settings_bp = Blueprint('settings', __name__)

from services.ai_status import AIStatusChecker

@settings_bp.route('/settings')
def settings_page():
    ai_status = {
        'llama': AIStatusChecker.check_llama(),
        'gemini': AIStatusChecker.check_gemini()
    }
    return render_template('settings.html', 
                           ai_status=ai_status,
                           partial=request.args.get('partial'))

@settings_bp.route('/settings/backup')
def backup_db():
    import tempfile
    import sqlite3
    from database.connection import get_db_connection
    
    if os.path.exists(DB_PATH):
        try:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, 'finance_backup_temp.db')
            
            src = get_db_connection()
            dst = sqlite3.connect(temp_path)
            src.backup(dst)
            src.close()
            dst.close()
            
            return send_file(temp_path, as_attachment=True, download_name='finance_backup.db')
        except Exception as e:
            return f"Backup failed: {str(e)}", 500
    return "No database found to backup.", 404

@settings_bp.route('/settings/restore', methods=['POST'])
def restore_db():
    if 'file' not in request.files:
        return redirect(url_for('settings.settings_page'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('settings.settings_page'))
    
    if file:
        import tempfile
        import sqlite3
        from database.connection import get_db_connection
        
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'finance_uploaded_temp.db')
        file.save(temp_path)
        
        try:
            src = sqlite3.connect(temp_path)
            dst = get_db_connection()
            src.backup(dst)
            src.close()
            dst.close()
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            # Trigger refresh of summaries and metrics after restore
            from services.analytics_service import AnalyticsService
            AnalyticsService.refresh_summaries()
            
            return "Database restored successfully!", 200
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return f"Restore failed: {str(e)}", 500

@settings_bp.route('/settings/reset', methods=['POST'])
def reset_database():
    from flask import jsonify
    from database.connection import reset_db
    try:
        reset_db()
        return jsonify({"status": "success", "message": "Database reset successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
