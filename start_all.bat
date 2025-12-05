@echo off
REM Start all bots in parallel using venv Python

echo Starting all trading bots with venv...
echo.

REM Activate venv and start bots in separate windows
REM Start EMA Pullback Bot
if exist "bots\bot_ema_pullback.py" (
    start "EMA Pullback Bot" cmd /k python -m bots.bot_ema_pullback
    echo ✓ EMA Pullback Bot iniciado
) else (
    echo ✗ Error: bots\bot_ema_pullback.py no encontrado
)

REM Start Round Levels Bot
if exist "bots\bot_round_levels.py" (
    start "Round Levels Bot" cmd /k python -m bots.bot_round_levels
    echo ✓ Round Levels Bot iniciado
) else (
    echo ✗ Error: bots\bot_round_levels.py no encontrado
)

echo.
echo Todos los bots estan corriendo en ventanas separadas.
echo Cierra cada ventana para detener el bot.
pause
