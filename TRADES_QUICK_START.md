# 🚀 Guía Rápida - Sistema de Logging de Trades

## ¿Qué es?

Sistema automático que registra cada operación del bot con:
- ✅ Indicadores técnicos (RSI, EMA, ATR, etc)
- ✅ Niveles de soporte/resistencia
- ✅ Patrón detectado y score
- ✅ Resultado (WIN/LOSS)
- ✅ P/L por operación

Todo se guarda en **CSV compatible con Excel**.

## 📦 Archivos Incluidos

| Archivo | Función |
|---------|---------|
| `trade_logger.py` | Módulo de logging (integrado en main.py) |
| `analyze_trades.py` | Análisis y reportes detallados |
| `trades_dashboard.py` | Dashboard en tiempo real |
| `demo_trades.py` | Crear trades de demostración |

## 🎯 Uso Rápido

### 1️⃣ El bot registra automáticamente

Cuando ejecutas `main.py`, cada operación se guarda en:
```
logs/trades/trades_20251124.csv
```

### 2️⃣ Ver resumen del día

```bash
python analyze_trades.py
```

Salida:
```
✅ Ganadas: 12 (80.0%)
❌ Perdidas: 3 (20.0%)
📈 Winrate: 80.0%
💰 Ganancia: $152.83
📊 Neto: $152.83
```

### 3️⃣ Ver qué indicadores funcionan mejor

```bash
python analyze_trades.py --indicators
```

Identifica:
- RSI funciona bien
- Triángulos no funcionan
- Soporte/resistencia tiene 87.5% de precisión

### 4️⃣ Monitorear en tiempo real

```bash
python trades_dashboard.py
```

Muestra:
- Últimos 10 trades
- Estadísticas por par
- Patrones más efectivos
- Todo en terminal con actualización automática

### 5️⃣ Exportar a Excel

```bash
python analyze_trades.py --export
```

Genera `trades_export_20251124.csv` que abre en Excel/Sheets.

## 📊 Ejemplos de Uso Real

### Encontrar el par que más gana
```bash
python analyze_trades.py --pairs
```

### Auditar un trade específico
```bash
python analyze_trades.py --trade-id 12345
```

### Revisar trades de hace 3 días
```bash
python analyze_trades.py --date 20251122
```

## 🔍 Columns en el CSV

```
timestamp       → Hora exacta del trade
trade_id        → Identificador único
pair            → EURUSD_otc, GBPUSD_otc, etc
timeframe       → M5, M15, M30
decision        → BUY o SELL
signal_score    → 1-7 (qué tan fuerte fue la señal)
pattern         → Breakout, Compression, etc
price           → Precio de entrada
ema             → Valor de media móvil
rsi             → Índice de Fuerza Relativa (0-100)
ema_conf        → Confirmación EMA (-1,0,1)
atr             → Average True Range
triangle        → Compresión detectada (0/1)
reversal        → Vela de reversión (0/1)
support_level   → Nivel de soporte
resistance_lvl  → Nivel de resistencia
result          → WIN / LOSS
profit_loss     → Ganancias en USD
expiry_time     → Duración en segundos
```

## 💡 Cómo Usar Para Mejorar el Bot

### Paso 1: Recolectar datos
Ejecuta el bot durante varias horas para tener datos.

### Paso 2: Analizar indicadores
```bash
python analyze_trades.py --indicators
```

### Paso 3: Identificar problemas
- RSI bajo WR → reducir peso o descartar
- Triángulos alto WR → aumentar confianza
- EURUSD bajo WR → deshabilitar par

### Paso 4: Ajustar main.py
Modifica `RSI_OVERSOLD`, `MIN_SCORE_BASE`, etc basado en los insights.

### Paso 5: Recolectar más datos
Vuelve a paso 1 para validar cambios.

## 🎮 Demo Rápida

Crear 20 trades ficticios para probar:
```bash
python demo_trades.py 20
python demo_trades.py --results
python analyze_trades.py --summary
```

## ⚙️ Integración en main.py

El logging está automáticamente integrado. Simplemente:

1. **Ejecuta main.py** - Las operaciones se guardan automáticamente
2. **Ejecuta analyze_trades.py** - Obtén insights
3. **Ejecuta trades_dashboard.py** - Monitorea en tiempo real

No necesitas hacer nada especial.

## 📈 Qué Puedes Descubrir

✅ Cuál es tu mejor par de divisas  
✅ En qué timeframe tienes mejor winrate  
✅ Qué patrón funciona mejor  
✅ Qué indicador es más preciso  
✅ Cuál es tu mejor hora del día  
✅ Cuándo deberías parar de tradear  

## 🎯 Próximos Pasos

1. Ejecuta `main.py` con el bot real
2. Cada hora, ejecuta `python trades_dashboard.py` para monitorear
3. Al final del día: `python analyze_trades.py --all`
4. Análisis semanal: `python analyze_trades.py --date YYYYMMDD`

## ❓ Problemas Comunes

**P: No veo archivos CSV**
R: Asegúrate que el bot ejecutó operaciones. Mira en `logs/trades/`

**P: ¿Dónde se guardan los datos?**
R: En `logs/trades/trades_YYYYMMDD.csv` (uno por día)

**P: ¿Puedo editar los CSV?**
R: Sí, pero mejor hacerlo vía Python para no romper el formato.

**P: ¿Se sincroniza con Google Sheets?**
R: No todavía, pero los CSV abiertos en Sheets siempre están actualizados.

## 📱 Tips Pro

- Abre el CSV en Google Sheets para compartir con otros
- Crea gráficos de equity curve en Sheets
- Filtra por pair para identificar patrones
- Ordena por RSI para ver qué values generan ganancias
- Busca trades perdidos para aprender de errores

---

**¿Necesitas ayuda?** Mira `TRADES_LOGGING_README.md` para documentación completa.
