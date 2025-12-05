#!/bin/bash
# Start all 3 bots in parallel

echo "🚀 Starting all trading bots..."

# Start each bot in background
python bots/bot_ema_pullback.py &
PID1=$!
echo "✅ EMA Pullback Bot started (PID: $PID1)"

python bots/bot_trend_following.py &
PID2=$!
echo "✅ Trend Following Bot started (PID: $PID2)"

python bots/bot_round_levels.py &
PID3=$!
echo "✅ Round Levels Bot started (PID: $PID3)"

echo ""
echo "📊 All bots running. Press Ctrl+C to stop all."
echo "PIDs: $PID1, $PID2, $PID3"

# Wait for all processes
wait
