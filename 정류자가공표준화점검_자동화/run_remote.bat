@echo off
echo ========================================================
echo  DC V5 Remote Access Launcher (No Account Needed)
echo ========================================================
echo.
echo This script uses Serveo.net to create a temporary public link.
echo.
echo [INSTRUCTIONS]
echo 1. Keep this window OPEN.
echo 2. Look for a URL like "https://something.serveo.net" below.
echo 3. Copy that URL.
echo 4. Paste it into the App's "Manual Public URL" field to get a QR code.
echo.
echo Connecting to server...
echo.
ssh -R 80:localhost:8501 serveo.net
pause
