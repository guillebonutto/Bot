@echo off
REM Start all 3 bots in parallel (Windows)

echo Starting all trading bots...

REM Start each bot in new window
start "EMA Pullback Bot" python bots/bot_ema_pullback.py
echo EMA Pullback Bot started

start "Trend Following Bot" python bots/bot_trend_following.py
echo Trend Following Bot started

start "Round Levels Bot" python bots/bot_round_levels.py
echo Round Levels Bot started

echo.
echo All bots running in separate windows.
echo Close each window to stop the respective bot.
pause
