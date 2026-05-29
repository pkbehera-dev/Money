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
        'gemini': AIStatusChecker.check_gemini(),
        'ollama_model': AIStatusChecker.get_ollama_model_name()
    }
    
    # Get current saved Gemini key (masked) for display
    current_gemini_key = ''
    try:
        from database.connection import get_db_connection
        conn = get_db_connection()
        row = conn.execute("SELECT config_value FROM system_config WHERE config_key = 'gemini_api_key'").fetchone()
        if row and row['config_value']:
            key = row['config_value']
            current_gemini_key = key[:8] + '•' * (len(key) - 12) + key[-4:] if len(key) > 12 else '•' * len(key)
        elif os.environ.get('GEMINI_API_KEY'):
            key = os.environ.get('GEMINI_API_KEY')
            current_gemini_key = key[:8] + '•' * (len(key) - 12) + key[-4:] if len(key) > 12 else '•' * len(key)
        conn.close()
    except Exception:
        pass
    
    return render_template('settings.html', 
                           ai_status=ai_status,
                           current_gemini_key=current_gemini_key,
                           partial=request.args.get('partial'))

@settings_bp.route('/settings/backup')
def backup_db():
    import tempfile
    import sqlite3
    import datetime
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
            
            date_str = datetime.date.today().strftime("%Y-%m-%d")
            filename = f"backup_financepro_{date_str}.db"
            return send_file(temp_path, as_attachment=True, download_name=filename)
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

@settings_bp.route('/settings/profile', methods=['POST'])
def update_profile():
    name = request.form.get('user_name', '').strip()
    nickname = request.form.get('user_nickname', '').strip()
    if name:
        from database.connection import get_db_connection
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES ('user_name', ?)", (name,))
        if nickname:
            conn.execute("INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES ('user_nickname', ?)", (nickname,))
        conn.commit()
        conn.close()
    return redirect(url_for('settings.settings_page'))


@settings_bp.route('/settings/update_api_key', methods=['POST'])
def update_api_key():
    from flask import jsonify
    gemini_key = request.form.get('gemini_api_key', '').strip()
    
    if not gemini_key:
        return redirect(url_for('settings.settings_page'))
    
    try:
        from database.connection import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES ('gemini_api_key', ?)",
            (gemini_key,)
        )
        conn.commit()
        conn.close()
        
        # Set it in the environment immediately so the running process uses it
        os.environ['GEMINI_API_KEY'] = gemini_key
        
        # Reset the cached Gemini client so the next call uses the new key
        try:
            from services.ai_services import GeminiService
            GeminiService._client = None
        except Exception:
            pass
        
    except Exception as e:
        pass
    
    return redirect(url_for('settings.settings_page'))

@settings_bp.route('/settings/updates')
def updates_page():
    from services.license_service import APP_VERSION, check_license_online, get_saved_license
    import datetime
    
    # Defaults
    expiry_date = "N/A"
    license_type = "Free Trial / Not Activated"
    
    try:
        key = get_saved_license()
        if key:
            res = check_license_online(key)
            if res.get('success'):
                expires_at = res.get('expires_at')
                expiry_date = expires_at if expires_at else "Lifetime License"
                license_type = "Pro Lifetime Member" if not expires_at else "Pro Member"
    except Exception:
        pass
        
    # Start date logic
    start_date = "N/A"
    try:
        from database.connection import get_db_connection
        conn = get_db_connection()
        row = conn.execute("SELECT MIN(date) as first_date FROM transactions").fetchone()
        if row and row['first_date']:
            start_date = row['first_date']
        else:
            row_config = conn.execute("SELECT created_at FROM loans ORDER BY created_at ASC LIMIT 1").fetchone()
            if row_config and row_config['created_at']:
                start_date = row_config['created_at'].split(' ')[0]
            else:
                start_date = datetime.date.today().strftime("%Y-%m-%d")
        conn.close()
    except Exception:
        pass

    return render_template('updates.html',
                           app_version=APP_VERSION,
                           start_date=start_date,
                           expiry_date=expiry_date,
                           license_type=license_type,
                           partial=request.args.get('partial'))

@settings_bp.route('/settings/check_update', methods=['POST'])
def run_update_check():
    from flask import jsonify
    from services.license_service import VERSION_URL, APP_VERSION
    import requests
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        import time
        cache_buster_url = f"{VERSION_URL}?t={int(time.time())}"
        response = requests.get(cache_buster_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            online_version = data.get("version")
            download_url = data.get("download_url")
            
            update_available = (online_version and online_version != APP_VERSION)
            return jsonify({
                "success": True,
                "current_version": APP_VERSION,
                "online_version": online_version,
                "update_available": update_available,
                "download_url": download_url
            })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    return jsonify({"success": False, "message": "Failed to check version"}), 400

@settings_bp.route('/settings/install_update', methods=['POST'])
def install_update():
    from flask import jsonify, request
    from services.license_service import perform_auto_update
    from threading import Thread
    
    download_url = request.json.get('download_url')
    if not download_url:
        return jsonify({"success": False, "message": "Missing download URL"}), 400
        
    try:
        # Run perform_auto_update in a background thread to prevent blocking Flask's json return
        # Disable native Tkinter window since we are spawning this in background of Flask process
        t = Thread(target=perform_auto_update, args=(download_url,), daemon=True)
        t.start()
        return jsonify({"success": True, "message": "Update download started."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@settings_bp.route('/settings/download_status')
def download_status():
    from flask import jsonify
    from services.license_service import get_update_progress
    return jsonify(get_update_progress())

@settings_bp.route('/settings/activate_new_license', methods=['POST'])
def activate_new_license():
    from flask import jsonify, request
    from services.license_service import check_license_online, save_license_locally
    from database.connection import get_db_connection
    import datetime
    
    license_key = request.json.get('license_key')
    if not license_key:
        return jsonify({"success": False, "message": "License key is required."}), 400
        
    try:
        # Verify the license key online
        res = check_license_online(license_key)
        if res.get('success'):
            # Save license locally
            save_license_locally(license_key)
            
            # Reset the activation date and cached expiry in the DB
            conn = get_db_connection()
            # Set activation date to today
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            conn.execute("INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES ('license_activated_at', ?)", (today_str,))
            
            expires_at = res.get('expires_at')
            if expires_at:
                conn.execute("INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES ('license_expiry', ?)", (expires_at,))
            else:
                conn.execute("DELETE FROM system_config WHERE config_key = 'license_expiry'")
                
            conn.commit()
            conn.close()
            
            # Return success details
            return jsonify({
                "success": True, 
                "message": "Activation successful!",
                "expires_at": expires_at or "Lifetime License"
            })
        else:
            return jsonify({"success": False, "message": res.get('message', 'Invalid key.')}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


