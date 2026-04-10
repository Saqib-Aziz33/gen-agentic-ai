@echo off
echo ========================================
echo  News & Research Telegram Bot
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo.
    echo Please create a .env file with your API keys:
    echo   - OPENAI_API_KEY
    echo   - TAVILY_API_KEY
    echo   - TELEGRAM_BOT_TOKEN
    echo.
    echo See .env.example for reference.
    echo.
    pause
    exit /b 1
)

REM Check if python-telegram-bot is installed
python -c "import telegram" 2>nul
if errorlevel 1 (
    echo [INFO] Installing python-telegram-bot...
    pip install python-telegram-bot
    if errorlevel 1 (
        echo [ERROR] Failed to install python-telegram-bot
        pause
        exit /b 1
    )
    echo [SUCCESS] python-telegram-bot installed successfully!
    echo.
)

echo [INFO] Starting Telegram Bot...
echo [INFO] Press Ctrl+C to stop the bot
echo.

python bot.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot stopped with an error.
    echo Check the logs above for details.
)

pause
