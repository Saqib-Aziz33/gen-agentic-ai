@echo off
echo ========================================
echo  Gift Recommendation Chatwoot Bot
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo.
    echo Please create a .env file with your API keys:
    echo   - OPENAI_API_KEY
    echo   - TAVILY_API_KEY
    echo   - CHATWOOT_ACCESS_TOKEN
    echo.
    echo See .env.example for reference.
    echo.
    pause
    exit /b 1
)

echo [INFO] Starting Gift Recommendation Chatwoot Bot...
echo [INFO] Webhook URL: http://localhost:5000/webhook
echo [INFO] Press Ctrl+C to stop the server
echo.

python chatwoot_bot.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot stopped with an error.
    echo Check the logs above for details.
)

pause
