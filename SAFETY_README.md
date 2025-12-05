# CRITICAL SAFETY DOCUMENTATION

## ⚠️ DEMO MODE SYSTEM

This bot now includes a **mandatory demo_mode flag** to prevent catastrophic financial losses.

### Configuration (config.yaml)

```yaml
system:
  demo_mode: true  # CRITICAL: Set to false ONLY for real trading
```

### Safety Levels

#### DEMO MODE (demo_mode: true)
- **Purpose**: Data collection and testing
- **Behavior**: Risk checks log warnings but DON'T block trades
- **Max Drawdown**: Can be set up to 100% for testing
- **Daily Limits**: Bypassed with warnings
- **Streak Limits**: Bypassed with warnings
- **Use Case**: Paper trading, backtesting, data farming

#### REAL MODE (demo_mode: false)
- **Purpose**: Live trading with real money
- **Behavior**: ALL risk checks are STRICTLY enforced
- **Max Drawdown**: HARD LIMIT of 20% (bot will crash if you try to set higher)
- **Daily Limits**: Enforced (default: 3 losses, 10 trades)
- **Streak Limits**: Enforced (default: 2 consecutive losses)
- **Use Case**: Production trading ONLY

### Runtime Assertions

The bot will **CRASH IMMEDIATELY** if:
```python
demo_mode = False AND max_drawdown > 0.20
```

Error message:
```
🚨 FATAL: max_drawdown=95% is SUICIDAL for real trading.
Maximum allowed in real mode is 20%. Set demo_mode=True for testing or reduce max_drawdown.
```

### Warning System

When `demo_mode: true`, the bot displays:
```
================================================================================
⚠️  DEMO MODE ENABLED - RISK CHECKS WILL BE BYPASSED
⚠️  THIS IS FOR DATA COLLECTION ONLY
⚠️  NEVER USE demo_mode=True IN REAL TRADING
================================================================================
```

### Code-Level Protection

In `risk_manager.py`, the following block is **MANDATORY**:

```python
###########################################################################
#                    ¡¡ ADVERTENCIA NUCLEAR !!
# Si estás en cuenta real y esta sección está comentada o ignorada,
# vas a perder todo tu dinero en menos de 48 horas.
# Responsable: quien haya tocado este archivo sin leer esto.
###########################################################################
```

### Safe Defaults

**config.yaml defaults:**
- `demo_mode: true` (safe for testing)
- `max_drawdown: 0.10` (10% - safe for real trading)
- `max_daily_losses: 3`
- `max_daily_trades: 10`
- `streak_limit: 2`

### Before Going Live

**CHECKLIST:**
1. ✅ Set `demo_mode: false` in config.yaml
2. ✅ Verify `max_drawdown <= 0.20` (20% maximum)
3. ✅ Test in paper trading for at least 1 week
4. ✅ Review all logs for errors
5. ✅ Confirm Telegram alerts are working
6. ✅ Start with MINIMUM position size
7. ✅ Monitor first 24 hours continuously

### Data Leakage Prevention

The ML pipeline has been verified to NOT include:
- `profit` or `profit_loss` as features
- `result` (WIN/LOSS) as a feature (only as label)
- Any future data in training features

Only the `label` column (1=win, 0=loss) is used as the target variable.

### Emergency Stop

If the bot is losing money in real mode:
1. Press Ctrl+C to stop
2. Set `demo_mode: true` in config.yaml
3. Review logs and trades
4. DO NOT restart in real mode until issue is identified

---

**Last Updated**: 2025-11-28
**Responsible**: AI Safety Refactor
