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
    if os.path.exists(DB_PATH):
        return send_file(DB_PATH, as_attachment=True, download_name='finance_backup.db')
    return "No database found to backup.", 404

@settings_bp.route('/settings/restore', methods=['POST'])
def restore_db():
    if 'file' not in request.files:
        return redirect(url_for('settings.settings_page'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('settings.settings_page'))
    
    if file:
        file.save(DB_PATH)
        return "Database restored successfully. Please restart the app.", 200
