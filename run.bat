@echo off
title Money App Launcher
echo ====================================================
echo               STARTING MONEY APP...
echo ====================================================
echo.
echo Launching Google Chrome in App Mode...
start chrome --app="%~dp0loading.html" --start-maximized
echo.
echo Launching Flask server (python app.py)...
echo (Keep this window open to run the server. Press Ctrl+C to stop.)
echo.
python app.py
echo.
echo Server has stopped.
pause
