# 📊 Trade Logger System

Sistema completo para registrar y analizar cada operación del bot con estructura detallada.

## 📋 Estructura del CSV

Cada trade se guarda con la siguiente estructura:

```
timestamp    pair          timeframe  decision  signal_score  pattern_detected
price        ema           rsi        ema_conf  tf_signal     atr
triangle_active  reversal_candle  near_support  near_resistance  support_level
resistance_level  htf_signal  result    profit_loss  expiry_time  trade_id  notes
```

### Campos Principales

| Campo | Descripción |
|-------|-------------|
| **timestamp** | Fecha y hora del trade (YYYY-MM-DD HH:MM:SS UTC) |
| **trade_id** | ID único de la operación |
| **pair** | Par de divisas (EURUSD_otc, GBPUSD_otc, etc) |
| **timeframe** | Timeframe (M5, M15, M30) |
| **decision** | Dirección: BUY o SELL |
| **signal_score** | Score numérico del indicador (0-7) |
| **pattern_detected** | Patrón chartista detectado |

### Indicadores Técnicos

| Campo | Descripción |
|-------|-------------|
| **price** | Precio de entrada |
| **ema** | Media móvil exponencial |
| **rsi** | Índice de Fuerza Relativa (0-100) |
| **ema_conf** | Confirmación EMA (-1, 0, 1) |
| **tf_signal** | Señal de tendencia (-1, 0, 1) |
| **atr** | Average True Range (volatilidad) |
| **triangle_active** | Compresión detectada (0 o 1) |
| **reversal_candle** | Vela de reversión (0 o 1) |

### Niveles de Precio

| Campo | Descripción |
|-------|-------------|
| **near_support** | Cerca del soporte (True/False) |
| **near_resistance** | Cerca de la resistencia (True/False) |
| **support_level** | Nivel de soporte |
| **resistance_level** | Nivel de resistencia |

### Resultado

| Campo | Descripción |
|-------|-------------|
| **result** | WIN, LOSS o PENDING |
| **profit_loss** | Ganancia/Pérdida en USD |
| **expiry_time** | Duración del trade en segundos |

## 📁 Archivos Generados

```
logs/
├── trades/
│   ├── trades_20251124.csv   # Trades del 24 de Nov
│   ├── trades_20251125.csv   # Trades del 25 de Nov
│   └── ...
```

Cada día se crea un nuevo archivo automáticamente.

## 🛠️ Herramientas Disponibles

### 1. **analyze_trades.py** - Análisis Detallado

Analizar trades de un día específico:

```bash
# Resumen general (defecto)
python analyze_trades.py

# Resumen de un día específico
python analyze_trades.py --date 20251124

# Ver detalles de un trade específico
python analyze_trades.py --trade-id 12345

# Mostrar todo
python analyze_trades.py --all

# Estadísticas por par
python analyze_trades.py --pairs

# Análisis de indicadores (cuáles funcionan mejor)
python analyze_trades.py --indicators

# Exportar a Excel
python analyze_trades.py --export
```

### 2. **trades_dashboard.py** - Monitoreo en Tiempo Real

Dashboard en terminal que se actualiza automáticamente:

```bash
# Actualización cada 5 segundos (defecto)
python trades_dashboard.py

# Actualización cada 10 segundos
python trades_dashboard.py --interval 10
```

Muestra:
- Estadísticas en tiempo real
- Últimos 10 trades
- Estadísticas por par
- Patrones más efectivos

### 3. **trade_logger.py** - Módulo Principal (usado por main.py)

Integrado automáticamente en main.py. Proporciona:

```python
from trade_logger import trade_logger

# Registrar un trade ANTES del resultado
trade_logger.log_trade({
    'timestamp': datetime.utcnow(),
    'trade_id': '12345',
    'pair': 'EURUSD_otc',
    'timeframe': 'M15',
    'decision': 'BUY',
    'signal_score': 5,
    'pattern_detected': 'Breakout',
    # ... más campos
})

# Actualizar resultado después de expiración
trade_logger.update_trade_result(
    trade_id='12345',
    result='WIN',
    profit_loss=12.50
)

# Obtener estadísticas del día
stats = trade_logger.get_stats()
print(f"Winrate: {stats['winrate']:.1f}%")
```

## 📊 Ejemplos de Uso

### Ejemplo 1: Revisar trades de hoy

```bash
python analyze_trades.py --summary
```

Salida:
```
================================================================================
📊 ESTADÍSTICAS RESUMIDAS
================================================================================
Total Operaciones: 15
✅ Ganadas: 9 (60.0%)
❌ Perdidas: 6 (40.0%)
⏳ Pendientes: 0

📈 Winrate: 60.0%
💰 Ganancia: $87.50
💸 Pérdida: $45.00
📊 Resultado Neto: $42.50

💵 Promedio por operación:
   • Ganancia promedio: $9.72
   • Pérdida promedio: $7.50
   • Profit Factor: 1.94
```

### Ejemplo 2: Encontrar qué indicadores funcionan mejor

```bash
python analyze_trades.py --indicators
```

Salida:
```
📊 ANÁLISIS DE INDICADORES
================================================================================

🔹 RSI:
   Trades con RSI: 12 | Winrate: 66.7%
   Oversold (<30): 4 trades
   Overbought (>70): 3 trades

🔹 Triangle:
   Activos: 5 trades | WR: 80.0%

🔹 Support/Resistance:
   Near Support: 4 trades | WR: 75.0%
   Near Resistance: 3 trades | WR: 66.7%
```

### Ejemplo 3: Monitorear en tiempo real

```bash
python trades_dashboard.py
```

Muestra un dashboard que se actualiza cada 5 segundos con:
- Estadísticas globales
- Últimos 10 trades ejecutados
- Performance por par
- Patrones más efectivos

### Ejemplo 4: Exportar a Excel

```bash
python analyze_trades.py --export
```

Genera archivo `trades_export_20251124.xlsx` con:
- Hoja 1: Todos los trades detallados
- Hoja 2: Resumen de estadísticas

## 🔧 Integración en main.py

El sistema está integrado automáticamente en `main.py`:

1. **Antes de operar**: Registra la operación con todos los indicadores
2. **Después de expirar**: Actualiza el resultado (WIN/LOSS)
3. **Campos capturados**: 
   - Indicadores técnicos
   - Niveles de soporte/resistencia
   - Score de la señal
   - Patrón detectado
   - Todas las métricas

## 📈 Cómo Usar los Datos

### Para Mejorar el Bot

1. **Ejecutar análisis diario**:
   ```bash
   python analyze_trades.py --indicators
   ```

2. **Identificar indicadores con mejor WR**:
   - Si RSI tiene 70% WR, aumentar peso en el scoring
   - Si Triangle tiene 50% WR, reducir o descartar
   - Si soporte/resistencia tiene 80% WR, validar más

3. **Detectar pares problemáticos**:
   ```bash
   python analyze_trades.py --pairs
   ```
   - Deshabilitar pares con WR < 40%
   - Aumentar timeframe en pares débiles

### Para Auditar Operaciones

1. **Ver detalles de un trade específico**:
   ```bash
   python analyze_trades.py --trade-id 98765
   ```

2. **Revisar trades perdidos**:
   - Analizar qué patrones fallaron
   - Correlacionar con RSI/EMA en esos momentos
   - Detectar sesgos en horarios específicos

## 💾 Formato CSV Completo

Cuando abres en Excel, verás columnas como:

```
timestamp | trade_id | pair | timeframe | decision | signal_score | pattern_detected | price | ema | rsi | ema_conf | tf_signal | atr | triangle_active | reversal_candle | near_support | near_resistance | support_level | resistance_level | htf_signal | result | profit_loss | expiry_time | notes
```

## 🎯 Ventajas del Sistema

✅ **Trazabilidad Completa**: Cada operación queda registrada con todos sus datos  
✅ **Análisis Automático**: Herramientas para extraer insights  
✅ **Excel Compatible**: Abre fácilmente en Excel/Sheets  
✅ **Histórico**: Todos los días quedan guardados  
✅ **Escalable**: Funciona con N operaciones  
✅ **Debugging**: Audita exactamente qué indicadores dispararon cada señal  

## 🚀 Próximas Mejoras (Opcionales)

- Gráficos de equity curve
- Heatmap de performance por par/hora
- Alertas automáticas si WR cae
- Sincronización con Google Sheets
- API para consultas históricas
