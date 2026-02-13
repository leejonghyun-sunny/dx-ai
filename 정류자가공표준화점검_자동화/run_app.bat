@echo off
setlocal
:: Change encoding to UTF-8
chcp 65001 > nul

echo ========================================================
echo  DC V5 Quality Inspection App Launcher v1.2
echo ========================================================
echo.
echo [LOG] Setup started at %date% %time% > launcher_log.txt

:: Define Python Path explicitly found on system
set "PYTHON_EXE=C:\Users\NoteBook\AppData\Local\Programs\Python\Python313\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found at "%PYTHON_EXE%"
    echo [ERROR] Python not found at "%PYTHON_EXE%" >> launcher_log.txt
    
    echo [INFO] Trying 'python' command as fallback...
    set "PYTHON_EXE=python"
    python --version > nul 2>&1
    if %errorlevel% neq 0 (
        echo [CRITICAL] Python is not installed or not in PATH.
        echo [CRITICAL] Python is not installed or not in PATH. >> launcher_log.txt
        echo.
        echo Please install Python from https://www.python.org/downloads/
        echo and check "Add Python to PATH" during installation.
        pause
        exit /b
    )
)

echo [INFO] Using Python: %PYTHON_EXE%
echo [INFO] Using Python: %PYTHON_EXE% >> launcher_log.txt

:: Install Dependencies
echo [INFO] Checking dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip > nul 2>&1
"%PYTHON_EXE%" -m pip install -r requirements.txt >> launcher_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed. Check launcher_log.txt.
    echo [ERROR] Dependency installation failed. >> launcher_log.txt
    pause
    exit /b
)

echo.
echo [INFO] Starting Application...
echo [LOG] Starting streamlit... >> launcher_log.txt
echo.

:: Launch Streamlit
"%PYTHON_EXE%" -m streamlit run app.py

if %errorlevel% neq 0 (
    echo [ERROR] Application crashed. See above for details.
    echo [ERROR] Application crashed with code %errorlevel%. >> launcher_log.txt
    pause
) else (
    echo [INFO] Application closed.
    echo [LOG] Application closed normally. >> launcher_log.txt
)

endlocal
