@echo off
REM Start all bots in parallel using venv Python

echo Starting all trading bots with venv...

REM Start each bot in new window using venv Python
start "EMA Pullback Bot" python bots/bot_ema_pullback.py
echo EMA Pullback Bot started

start "Round Levels Bot" python bots/bot_round_levels.py
echo Round Levels Bot started

echo.
echo All bots running in separate windows.
echo Close each window to stop the respective bot.
pause
