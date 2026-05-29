import os
import sys
import uuid
import socket
import requests
import hashlib
import json

# Product config constants
APP_VERSION = "1.1.1"
VERSION_URL = "https://raw.githubusercontent.com/pkbehera-dev/Money/master/version.json"
PRODUCT_ID = "finance_pro"
ACTIVATION_URL = "https://service.pkbehera.in/api/activate"
LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".finance_pro_license")

# Global variables to track download progress dynamically
_update_status = "idle"
_update_percent = 0
_update_error = ""

_app_mutex = None

def create_app_mutex():
    global _app_mutex
    if sys.platform == 'win32':
        try:
            import ctypes
            _app_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "FinanceProMutexString")
        except Exception:
            pass

def release_app_mutex():
    global _app_mutex
    if _app_mutex and sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_app_mutex)
            _app_mutex = None
        except Exception:
            pass

def set_update_progress(status, percent, error=""):
    global _update_status, _update_percent, _update_error
    _update_status = status
    _update_percent = percent
    _update_error = error

def get_update_progress():
    global _update_status, _update_percent, _update_error
    return {
        "status": _update_status,
        "percent": _update_percent,
        "error": _update_error
    }

def get_device_fingerprint():
    # Retrieve a secure MAC address based identifier
    return str(uuid.getnode())

def check_license_online(key):
    payload = {
        "license_key": key,
        "product_id": PRODUCT_ID,
        "device_id": get_device_fingerprint(),
        "device_name": socket.gethostname()
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.post(ACTIVATION_URL, json=payload, headers=headers, timeout=8)
        return response.json()
    except Exception as e:
        return {"success": False, "unreachable": True, "message": f"Connection error: {str(e)}"}

def get_license_signature(key):
    hwid = get_device_fingerprint()
    return hashlib.sha256(f"{key}:{hwid}".encode()).hexdigest()

def save_license_locally(key):
    try:
        signature = get_license_signature(key)
        with open(LICENSE_FILE, 'w') as f:
            json.dump({
                "license_key": key,
                "signature": signature
            }, f)
    except Exception:
        pass

def get_saved_license():
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, 'r') as f:
                data = json.load(f)
                key = data.get("license_key")
                saved_sig = data.get("signature")
                if key and saved_sig == get_license_signature(key):
                    return key
        except Exception:
            return None
    return None

def perform_auto_update(download_url):
    """Downloads the new installer and spawns it silently to replace the application files."""
    import requests
    import subprocess
    import sys
    import os
    import time
    
    global _update_status
    
    # Guard: prevent concurrent downloads
    if _update_status == "downloading":
        return
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        set_update_progress("downloading", 0)
        # Determine executable path
        current_exe = sys.executable if getattr(sys, 'frozen', False) else None
        if not current_exe:
            set_update_progress("error", 0, "Application is not running as a packaged executable.")
            return
            
        # Download installer to Windows temp folder
        temp_dir = os.environ.get("TEMP", os.path.dirname(current_exe))
        temp_installer = os.path.join(temp_dir, "FinanceProSetup.exe")
        
        r = requests.get(download_url, headers=headers, stream=True)
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_installer, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                    else:
                        percent = min(99, int((downloaded / (50 * 1024 * 1024)) * 100))
                    set_update_progress("downloading", percent)
                            
        set_update_progress("installing", 100)
        
        # Sleep brief moment to allow UI polling to fetch the "installing" state
        time.sleep(2.0)
        
        # Release the Windows mutex handle to prevent the installer from detecting it
        release_app_mutex()
        
        # Launch the Inno Setup installer silently after a 1-second delay (via ping)
        # to ensure the parent process has fully terminated and released the file lock
        cmd = f'ping 127.0.0.1 -n 2 > nul && start "" "{temp_installer}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
        subprocess.Popen(cmd, shell=True)
        
        # Exit immediately to release file lock on our executable so installer can overwrite it
        os._exit(0)
    except Exception as e:
        set_update_progress("error", 0, str(e))


