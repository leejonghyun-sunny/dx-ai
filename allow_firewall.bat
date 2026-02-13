@echo off
echo ========================================================
echo  Streamlit Application Firewall Setup
echo ========================================================
echo.
echo This script will open TCP Port 8501 in Windows Firewall
echo to allow other devices to connect to this PC.
echo.
echo * Administrator privileges are required.
echo.
pause

netsh advfirewall firewall add rule name="Streamlit App (Port 8501)" dir=in action=allow protocol=TCP localport=8501

echo.
echo ========================================================
echo  Rule Added Successfully!
echo ========================================================
echo.
pause
