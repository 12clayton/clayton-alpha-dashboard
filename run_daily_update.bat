@echo off
setlocal

set "PROJECT_DIR=C:\Users\16355\Desktop\Global_QDII_Risk_Monitor"
cd /d "%PROJECT_DIR%"

if not exist "logs" mkdir "logs"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%i"
set "LOG_FILE=%PROJECT_DIR%\logs\daily_update_%TODAY%.log"

echo ================================================== > "%LOG_FILE%"
echo Global QDII Risk Monitor daily update >> "%LOG_FILE%"
echo Run date: %TODAY% >> "%LOG_FILE%"
echo Project: %PROJECT_DIR% >> "%LOG_FILE%"
echo This script only generates research reports and does not trade. >> "%LOG_FILE%"
echo ================================================== >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo [1/3] Enter project directory... >> "%LOG_FILE%"
cd /d "%PROJECT_DIR%" >> "%LOG_FILE%" 2>&1

echo [2/3] Run python main.py to generate risk report and news digest... >> "%LOG_FILE%"
python main.py >> "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo. >> "%LOG_FILE%"
echo [3/3] Finished with exit code %EXIT_CODE%. >> "%LOG_FILE%"
echo Log saved to: %LOG_FILE% >> "%LOG_FILE%"

exit /b %EXIT_CODE%
