# 3-Bot Architecture - README

## Quick Start

### 1. Setup Environment

Copy your credentials to `.env`:
```bash
cp .env.example .env
# Edit .env with your POCKETOPTION_SSID, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
```

### 2. Run Individual Bot

```bash
# EMA Pullback (M1/M5, Fibonacci retracements)
python bots/bot_ema_pullback.py

# Trend Following (H1/M5, multi-timeframe)
python bots/bot_trend_following.py

# Round Levels (M5/M15, .000/.500 rejections)
python bots/bot_round_levels.py
```

### 3. Run All Bots

**Linux/Mac:**
```bash
chmod +x start_all.sh
./start_all.sh
```

**Windows:**
```cmd
start_all.bat
```

---

## Bot Strategies

### Bot #1: EMA Pullback
- **Timeframes**: M1, M5
- **Strategy**: Fibonacci pullback + EMA confirmation
- **ML Threshold**: 65%
- **Best for**: Range-bound markets with clear trends

**Conditions:**
1. Price above/below EMA20 and EMA50
2. Pullback to 38.2% or 61.8% Fibonacci
3. RSI 40-60 (not extreme)
4. Rejection candle (pin bar)

### Bot #2: Trend Following
- **Timeframes**: H1 (confirmation), M5 (entry)
- **Strategy**: Multi-timeframe trend alignment
- **ML Threshold**: 60%
- **Best for**: Strong trending markets

**Conditions:**
1. H1: ADX > 25 (strong trend)
2. H1: EMA alignment
3. M5: EMA cross in trend direction
4. M5: MACD confirmation

### Bot #3: Round Levels
- **Timeframes**: M5, M15
- **Strategy**: Rejection from psychological levels
- **ML Threshold**: 70%
- **Best for**: High-probability reversals

**Conditions:**
1. Price near .000 or .500 level
2. Rejection candle (wick > 2x body)
3. Volume spike (if available)
4. No news events

---

## ML Models

Each bot uses its own trained model:
- `models/ema_pullback_model.pkl`
- `models/trend_following_model.pkl`
- `models/round_levels_model.pkl`

**To train models**, use `generator_demo_pro.py` with strategy-specific filters.

---

## Logs

Each bot creates its own log file:
- `logs/bot_ema_pullback.log`
- `logs/bot_trend_following.log`
- `logs/bot_round_levels.log`

---

## Configuration

All bots share the same `config.yaml` for:
- Pairs to trade
- Risk management settings
- Timeframe definitions

Bot-specific settings (ML threshold, sleep interval) are in `.env` or hardcoded.

---

## Monitoring

All bots send alerts to the same Telegram channel (configured in `.env`).

Messages are prefixed with bot name:
- `[ema_pullback] 🚀 Signal found...`
- `[trend_following] 📊 H1 trend confirmed...`
- `[round_levels] 💎 Level rejection detected...`

---

## Stopping Bots

**Individual:**
- Press `Ctrl+C` in the bot's terminal

**All (Linux/Mac):**
```bash
pkill -f "python bots/bot_"
```

**All (Windows):**
- Close each bot window, or use Task Manager

---

## Next Steps

1. **Test each bot individually** with demo account
2. **Generate historical data** for each strategy
3. **Train ML models** using `generator_demo_pro.py`
4. **Monitor performance** and adjust thresholds
5. **Deploy to production** when confident

---

## Architecture

```
bots/
├── __init__.py
├── base_bot.py              # Shared base class
├── ml_filter.py             # Common ML filter
├── bot_ema_pullback.py      # Bot #1
├── bot_trend_following.py   # Bot #2
└── bot_round_levels.py      # Bot #3
```

**Benefits:**
- ✅ Each bot is independent
- ✅ Easy to test/debug individually
- ✅ Specialized strategies = higher win rate
- ✅ ML models trained per strategy
- ✅ Simple to add Bot #4, #5, etc.
