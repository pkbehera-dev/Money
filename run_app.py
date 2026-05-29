import os
import sys
import json
import uuid
from threading import Thread
import webview  # pywebview for native window

# Configuration constants
from services.license_service import (
    APP_VERSION, VERSION_URL, PRODUCT_ID, ACTIVATION_URL, LICENSE_FILE,
    get_device_fingerprint, check_license_online,
    get_license_signature, save_license_locally, get_saved_license,
    perform_auto_update, create_app_mutex
)

APP_NAME = f"Finance Pro v{APP_VERSION}"


class ActivationAPI:
    """Python API exposed to the pywebview activation window's JavaScript."""
    def __init__(self, window_ref):
        self._window = window_ref
        self.activated = False

    def activate(self, key):
        if not key or not key.strip():
            return {"success": False, "message": "Please enter a license key."}
        key = key.strip()
        res = check_license_online(key)
        if res.get("success"):
            save_license_locally(key)
            self.activated = True
            expires_at = res.get("expires_at")
            expiry_msg = f"Expires on: {expires_at}" if expires_at else "Lifetime License activated!"
            return {"success": True, "message": f"Activation successful! {expiry_msg}"}
        else:
            return {"success": False, "message": res.get("message", "Invalid or expired license key.")}

    def close_window(self):
        if self._window:
            self._window.destroy()

    def get_hwid(self):
        return get_device_fingerprint()


def show_activation_window():
    """Shows a premium pywebview-based activation window. Returns True if activated."""
    hwid = get_device_fingerprint()

    activation_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Finance Pro — Activate</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0b0d10;
                --card-bg: rgba(17, 22, 34, 0.65);
                --card-border: rgba(59, 130, 246, 0.15);
                --accent: #3b82f6;
                --accent-hover: #2563eb;
                --success: #10b981;
                --danger: #ef4444;
                --text: #f5f6f8;
                --text-muted: #8892b0;
                --input-bg: #1e293b;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: var(--bg);
                color: var(--text);
                font-family: 'Outfit', 'Segoe UI', sans-serif;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
                background-image: radial-gradient(circle at 50% 40%, rgba(59, 130, 246, 0.08) 0%, transparent 60%);
            }}
            .card {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 24px;
                padding: 40px 36px;
                width: 100%;
                max-width: 420px;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(16px);
                text-align: center;
            }}
            .logo {{ font-size: 2.4rem; margin-bottom: 8px; filter: drop-shadow(0 0 12px rgba(59, 130, 246, 0.4)); }}
            h1 {{ font-size: 1.4rem; font-weight: 800; margin-bottom: 4px; letter-spacing: -0.01em; }}
            .dev {{ font-size: 0.78rem; font-weight: 600; color: var(--success); margin-bottom: 16px; }}
            .desc {{ font-size: 0.88rem; color: var(--text-muted); margin-bottom: 24px; line-height: 1.45; }}
            .input-wrap {{ position: relative; margin-bottom: 12px; }}
            input {{
                width: 100%;
                padding: 14px 16px;
                background: var(--input-bg);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                color: var(--text);
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 0.92rem;
                text-align: center;
                outline: none;
                transition: border-color 0.2s;
            }}
            input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15); }}
            input::placeholder {{ color: #475569; }}
            .hwid {{ font-size: 0.72rem; color: #475569; font-style: italic; margin-bottom: 20px; }}
            .btn {{
                width: 100%;
                padding: 14px;
                background: var(--accent);
                color: white;
                border: none;
                border-radius: 12px;
                font-family: 'Outfit', sans-serif;
                font-size: 0.95rem;
                font-weight: 700;
                cursor: pointer;
                transition: background 0.2s, transform 0.1s;
                letter-spacing: 0.02em;
            }}
            .btn:hover {{ background: var(--accent-hover); transform: translateY(-1px); }}
            .btn:active {{ transform: translateY(0); }}
            .btn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}
            .status {{
                margin-top: 14px;
                font-size: 0.82rem;
                font-weight: 600;
                min-height: 20px;
                transition: color 0.2s;
            }}
            .status.success {{ color: var(--success); }}
            .status.error {{ color: var(--danger); }}
            .status.loading {{ color: var(--text-muted); }}
            .buy-link {{
                display: inline-block;
                margin-top: 18px;
                font-size: 0.8rem;
                color: var(--accent);
                text-decoration: underline;
                cursor: pointer;
                font-weight: 600;
            }}
            .buy-link:hover {{ color: var(--accent-hover); }}
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                20%, 60% {{ transform: translateX(-6px); }}
                40%, 80% {{ transform: translateX(6px); }}
            }}
            .shake {{ animation: shake 0.4s ease-in-out; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo">🔑</div>
            <h1>Activate Finance Pro</h1>
            <div class="dev">Developed by Pradyumna Behera (Bapun)</div>
            <div class="desc">Enter your license key below to unlock the full application experience.</div>
            <div class="input-wrap">
                <input type="text" id="key-input" placeholder="XXXX-XXXX-XXXX-XXXX" autofocus spellcheck="false" />
            </div>
            <div class="hwid">Device ID: {hwid}</div>
            <button class="btn" id="activate-btn" onclick="handleActivate()">Activate Device</button>
            <div class="status" id="status-msg"></div>
            <a class="buy-link" onclick="window.open('https://service.pkbehera.in/buy')">Don't have a key? Buy one here &rarr;</a>
        </div>
        <script>
            const input = document.getElementById('key-input');
            const btn = document.getElementById('activate-btn');
            const status = document.getElementById('status-msg');

            input.addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') handleActivate();
            }});

            async function handleActivate() {{
                const key = input.value.trim();
                if (!key) {{
                    status.className = 'status error';
                    status.innerText = 'Please enter a license key.';
                    input.classList.add('shake');
                    setTimeout(() => input.classList.remove('shake'), 500);
                    return;
                }}
                btn.disabled = true;
                btn.innerText = 'Activating...';
                status.className = 'status loading';
                status.innerText = 'Contacting activation server...';

                try {{
                    const result = await pywebview.api.activate(key);
                    if (result.success) {{
                        status.className = 'status success';
                        status.innerText = result.message;
                        btn.innerText = '✓ Activated';
                        setTimeout(() => {{
                            pywebview.api.close_window();
                        }}, 1200);
                    }} else {{
                        status.className = 'status error';
                        status.innerText = result.message;
                        btn.disabled = false;
                        btn.innerText = 'Activate Device';
                        input.classList.add('shake');
                        setTimeout(() => input.classList.remove('shake'), 500);
                    }}
                }} catch (err) {{
                    status.className = 'status error';
                    status.innerText = 'Connection failed. Check your internet.';
                    btn.disabled = false;
                    btn.innerText = 'Activate Device';
                }}
            }}
        </script>
    </body>
    </html>
    """

    # We need to create the window first, then pass it to the API
    api = ActivationAPI(None)
    window = webview.create_window(
        title="Finance Pro — Activate",
        html=activation_html,
        width=480,
        height=520,
        resizable=False,
        js_api=api,
        text_select=False
    )
    api._window = window
    webview.start()
    return api.activated


def start_flask_server():
    if getattr(sys, 'frozen', False):
        template_dir = os.path.join(sys._MEIPASS, 'ui', 'templates')
        static_dir = os.path.join(sys._MEIPASS, 'ui', 'static')
        
        from app import app
        app.template_folder = template_dir
        app.static_folder = static_dir
    else:
        from app import app

    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)



def main():
    # Create the named mutex for Inno Setup detection
    create_app_mutex()
    
    # 1. Check local key
    saved_key = get_saved_license()
    
    if saved_key:
        res = check_license_online(saved_key)
        if res.get("success") or res.get("unreachable"):
            launch_native_window()
            return
            
    # 2. Show activation window (pywebview-based, no tkinter)
    if show_activation_window():
        launch_native_window()


def launch_native_window():
    # Start flask server in background
    server_thread = Thread(target=start_flask_server, daemon=True)
    server_thread.start()

    # Generate a random money fact for the loading screen
    import random
    facts = [
        "A penny doubled every day for 30 days grows to over \u20b953.6 Lakhs (\u20b95,368,709.12) due to compound interest.",
        "The 'Rule of 72' estimates how long it takes to double your money: divide 72 by your annual interest rate.",
        "The word 'budget' comes from the Middle English word 'bougette', which means a small leather pouch or bag.",
        "Compound interest was called the 'eighth wonder of the world' by Albert Einstein.",
        "Paying yourself first\u2014putting money into savings before spending the rest\u2014is the #1 habit of wealth builders.",
        "The first paper money was created in China over 1,000 years ago during the Tang Dynasty.",
        "Tracking your expenses regularly reduces impulse spending by an average of 20% to 30%.",
        "Having an emergency fund covering 3-6 months of living expenses protects you from high-interest debt.",
        "The rupee symbol (\u20b9) was designed by D. Udaya Kumar and officially adopted by the Government of India in 2010.",
        "Automating your investments takes emotions out of market fluctuations and ensures consistent growth.",
        "Inflation means a rupee today is worth more than a rupee tomorrow. Invest to protect your purchasing power."
    ]
    random_fact = random.choice(facts)

    # Inline HTML for instant loading window
    loading_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Finance Pro</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #0b0d10;
                --accent-color: #3b82f6;
                --text-color: #f5f6f8;
                --text-muted: #8892b0;
                --card-bg: rgba(17, 22, 34, 0.65);
                --card-border: rgba(59, 130, 246, 0.15);
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background-color: var(--bg-color);
                color: var(--text-color);
                font-family: 'Outfit', sans-serif;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
                background-image: radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 60%);
            }}
            .container {{ text-align: center; width: 100%; max-width: 400px; padding: 20px; }}
            .card {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 24px;
                padding: 40px 30px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
                backdrop-filter: blur(16px);
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .logo-container {{
                position: relative;
                width: 80px;
                height: 80px;
                margin-bottom: 24px;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .pulse-ring {{
                position: absolute;
                width: 100%;
                height: 100%;
                border-radius: 50%;
                border: 2px solid var(--accent-color);
                animation: pulse 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
            }}
            .logo-icon {{
                font-size: 2.2rem;
                color: var(--accent-color);
                filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.4));
            }}
            h2 {{ font-size: 1.4rem; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.01em; }}
            p {{ color: var(--text-muted); font-size: 0.85rem; margin-bottom: 20px; }}
            .fact-card {{
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
                padding: 14px 18px;
                margin-bottom: 24px;
                text-align: left;
                width: 100%;
            }}
            .fact-header {{
                font-size: 0.68rem;
                font-weight: 800;
                color: var(--accent-color);
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 6px;
            }}
            .fact-text {{ font-size: 0.82rem; line-height: 1.4; color: #d1d5db; }}
            .progress-container {{
                width: 100%;
                background: rgba(255, 255, 255, 0.05);
                height: 5px;
                border-radius: 10px;
                overflow: hidden;
                margin-bottom: 16px;
            }}
            .progress-bar {{
                height: 100%;
                width: 0%;
                background: linear-gradient(90deg, var(--accent-color), #60a5fa);
                border-radius: 10px;
                transition: width 0.1s linear;
            }}
            .timer-text {{ font-size: 0.8rem; font-weight: 600; color: var(--accent-color); text-transform: uppercase; }}
            @keyframes pulse {{
                0% {{ transform: scale(0.8); opacity: 0.5; }}
                100% {{ transform: scale(1.3); opacity: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="logo-container">
                    <div class="pulse-ring"></div>
                    <div class="logo-icon">&#x26c1;</div>
                </div>
                <h2>Finance Pro</h2>
                <p>Starting secure backend systems...</p>
                <div class="fact-card">
                    <div class="fact-header">Financial Fact & Tip</div>
                    <div class="fact-text">{random_fact}</div>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" id="bar"></div>
                </div>
                <div class="timer-text" id="timer">Initializing... 0.0s</div>
            </div>
        </div>
        <script>
            const bar = document.getElementById('bar');
            const timerText = document.getElementById('timer');
            const targetUrl = "http://127.0.0.1:5000";
            
            let connected = false;
            let elapsed = 0;
            const startTime = Date.now();

            async function checkConnection() {{
                if (connected) return;
                try {{
                    await fetch(targetUrl + "/", {{ mode: "no-cors", cache: "no-store" }});
                    connected = true;
                    bar.style.transition = 'width 0.2s ease-out';
                    bar.style.width = '100%';
                    timerText.innerText = "Connected! Redirecting...";
                    setTimeout(() => {{
                        window.location.href = targetUrl;
                    }}, 250);
                }} catch (err) {{
                    setTimeout(checkConnection, 250);
                }}
            }}

            function animateProgress() {{
                if (connected) return;
                elapsed = Date.now() - startTime;
                let progress = 0;
                if (elapsed < 5000) {{
                    progress = (elapsed / 5000) * 90;
                }} else {{
                    progress = 90 + (1 - Math.exp(-(elapsed - 5000) / 10000)) * 8;
                }}
                bar.style.width = progress.toFixed(1) + '%';
                timerText.innerText = `Connecting... (${{(elapsed / 1000).toFixed(1)}}s)`;
                requestAnimationFrame(animateProgress);
            }}

            checkConnection();
            requestAnimationFrame(animateProgress);
        </script>
    </body>
    </html>
    """

    # Create native window targeting loading page
    window = webview.create_window(
        title="Finance Pro",
        html=loading_html,
        width=1280,
        height=800,
        resizable=True,
        text_select=True
    )
    
    webview.start()

if __name__ == '__main__':
    main()
