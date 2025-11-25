# 🤖 Integración ML + Trades - Documentación

## ¿Qué es?

Sistema que vincula el **modelo de IA** (`ML_pipeline_for_PocketOption_bot.py`) con el **logging de trades** (`trade_logger.py`).

**Beneficio:** El modelo aprende de cada operación ejecutada en tiempo real.

```
Bot ejecuta trade → Se guarda en CSV → Resultado se etiqueta → IA entrena → IA mejora
```

## 📊 Flujo de Datos

```
main.py (Bot)
    ↓ Detecta señal
    ↓ [NUEVO] Predice con IA la probabilidad de ganancia
    ↓ Ejecuta operación
    ↓ Espera resultado
    ↓ Guarda en trade_logger.py
    ↓ [NUEVO] Sincroniza con ML_pipeline_for_PocketOption_bot.py
    ↓ IA aprende del resultado
    ↓ Próxima iteración: modelo más inteligente
```

## 🎯 Archivos Principales

### 1. `ml_trades_integration.py` (NUEVO)
Vinculación entre IA y Trades:
- Convierte trades → features ML
- Sincroniza resultados automáticamente
- Retroalimentación continua

### 2. `main.py` (MODIFICADO)
Ahora incluye:
- ✅ Importa `ml_trades_integration`
- ✅ Predice probabilidad antes de operar
- ✅ Sincroniza resultados automáticamente

### 3. `ML_pipeline_for_PocketOption_bot.py` (EXISTENTE)
- Modelo de IA
- Entrenamiento automático
- Predicciones

### 4. `trade_logger.py` (EXISTENTE)
- Registra cada trade
- Guarda indicadores
- Almacena resultado

## ⚡ Comandos

### Sincronizar trades manualmente
```bash
python ml_trades_integration.py --sync
```

### Sincronizar y entrenar
```bash
python ml_trades_integration.py --sync-train
```

### Ver estadísticas
```bash
python ml_trades_integration.py --stats
```

### Exportar datos ML
```bash
python ml_trades_integration.py --export
```

## 🚀 Cómo Funciona en main.py

### 1. Antes de Operar (NUEVA PREDICCIÓN)

```python
if ML_AVAILABLE:
    ml_features = {
        'rsi': ...,
        'ema_conf': ...,
        'signal_score': ...,
        # ... otros indicadores
    }
    ml_prediction, ml_prob = predict_success(ml_features)
    
    # Mostrar probabilidad
    log(f"🤖 ML Predicción: {ml_prob:.1%}")
```

**Resultado:** Ves antes de operar qué probabilidad de éxito tiene el trade.

### 2. Después de Operar (SINCRONIZACIÓN AUTOMÁTICA)

```python
if ML_AVAILABLE:
    synced = ml_trades.sync_trades_to_ml(auto_train=False)
    log(f"✅ {synced} trades sincronizados")
```

**Resultado:** El resultado (WIN/LOSS) se guarda automáticamente en el modelo.

## 📈 Flujo de Aprendizaje

```
DÍA 1:
├─ 50 trades ejecutados
├─ 50 resultados guardados
├─ Modelo con datos de entrenamiento
└─ ⚠️ Modelo aún no es muy bueno

DÍA 2:
├─ Ejecutar: python ml_trades_integration.py --sync-train
├─ Modelo se entrena con 50 trades reales
├─ Accuracy mejora
└─ ✅ Siguientes predicciones más precisas

DÍA 3+:
├─ Ciclo se repite
├─ Modelo aprende patrones que funcionan
├─ Rechaza operaciones que normalmente pierden
└─ 🚀 Winrate mejora gradualmente
```

## 🔧 Mapeo de Campos

Cuando conviertes un trade → features ML:

| Campo CSV (trades) | Campo ML | Tipo |
|------------------|----------|------|
| rsi | rsi | float |
| ema_conf | ema_conf | int (-1,0,1) |
| tf_signal | tf_signal | int (-1,0,1) |
| triangle_active | triangle_active | int (0,1) |
| reversal_candle | reversal_candle | int (0,1) |
| near_support | near_support | int (0,1) |
| result | label | int (1=WIN, 0=LOSS) |
| ... | ... | ... |

## 📊 CSV Generados

### logs/trades/trades_YYYYMMDD.csv
```
timestamp | pair | decision | rsi | result | ...
```
Guardado automáticamente por `trade_logger.py`

### ml_data/features_log.csv
```
timestamp | pair | rsi | ema_conf | label | ...
```
Sincronizado automáticamente desde trades

### ml_data/model.pkl
Modelo ML entrenado (cargado automáticamente)

## 💡 Ejemplo Práctico

### Scenario 1: Sin IA
```
Bot: Detecta señal
Bot: Ejecuta sin vacilar
Resultado: 50% WIN, 50% LOSS (aleatorio)
```

### Scenario 2: Con IA
```
Bot: Detecta señal
Bot: Pregunta a IA "¿Qué probabilidad de ganar?"
IA: "72% de probabilidad"
Bot: "Ejecuta con confianza"
Bot: Si IA aprende bien → 70%+ winrate
```

## 🎓 Entrenar el Modelo Manualmente

### Opción 1: Auto (Recomendado)
```bash
# main.py sincroniza automáticamente
python main.py
```

### Opción 2: Manual
```bash
# Una vez al día o cuando quieras
python ml_trades_integration.py --sync-train
```

### Opción 3: Externo
```bash
# Exportar datos y entrenar en Jupyter/Python
python ml_trades_integration.py --export
# Ahora tienes ml_training_data.csv con todos los trades
```

## 📈 Monitoreo

### Ver si el modelo mejora
```bash
python ml_trades_integration.py --stats
```

Salida:
```
📊 ESTADÍSTICAS ML vs TRADES
==================================================
total_trades: 127
wins: 89
losses: 38
winrate: 70.1%
```

### Ver predicciones en vivo
- Ejecuta `main.py`
- Cada vez que detecta una señal, verás:
  ```
  🤖 ML Predicción: 72.5% de probabilidad de ganancia
  ```

## 🔄 Ciclo Completo (Recomendado)

```
HORA 1-8: Bot corre con main.py
├─ Ejecuta trades
├─ Sincroniza automáticamente con ML
└─ Predice en cada operación

HORA 9 (FIN DE DÍA): Entrenar modelo
├─ python ml_trades_integration.py --sync-train
└─ Modelo se entrena con todos los trades del día

HORA 10+: Análisis
├─ python analyze_trades.py --indicators
├─ python ml_trades_integration.py --stats
└─ Validar que IA está aprendiendo
```

## ⚙️ Configuración

En `ML_pipeline_for_PocketOption_bot.py`:

```python
PROB_THRESHOLD = 0.58  # ← Umbral mínimo para operar

# Valores recomendados:
# 0.50 = Operador agresivo (baja selectividad)
# 0.55 = Balanceado (recomendado)
# 0.60 = Conservador (alta selectividad)
```

## 🆘 Troubleshooting

### P: ¿Cómo sé si el modelo está aprendiendo?
**R:** Ejecuta `python ml_trades_integration.py --stats` cada día. El winrate debería mejorar.

### P: ¿Qué si el modelo está mal?
**R:** Probablemente le faltan datos. Ejecuta bot durante varios días primero (50+ trades).

### P: ¿Cómo reseteo el modelo?
**R:** Elimina:
- `ml_data/model.pkl`
- `ml_data/model_meta.json`

Se crearán nuevos en el próximo entrenamiento.

### P: ¿La predicción ML bloquea operaciones?
**R:** No. Es solo información. El bot aún ejecuta si crees que es buena señal.

## 📚 Referencia Rápida

| Comando | Resultado |
|---------|-----------|
| `python main.py` | Bot con IA automática |
| `python ml_trades_integration.py --sync` | Sincronizar sin entrenar |
| `python ml_trades_integration.py --sync-train` | Sincronizar y entrenar |
| `python ml_trades_integration.py --stats` | Ver performance |
| `python ml_trades_integration.py --export` | Exportar datos ML |

## 🚀 Próximos Pasos

1. ✅ Ejecuta `main.py` normalmente
2. ✅ El sistema sincroniza automáticamente
3. ✅ Al final del día: `python ml_trades_integration.py --sync-train`
4. ✅ Monitorea: `python ml_trades_integration.py --stats`
5. ✅ Observa cómo el winrate mejora gradualmente

## 📊 Ejemplo de Progresión

```
SEMANA 1:
├─ 200 trades
├─ Winrate: 52%
├─ Modelo: Nuevo (poca confianza)
└─ Predicciones: Aleatorias

SEMANA 2:
├─ 200 trades más
├─ Winrate: 58%
├─ Modelo: Mejor (empieza a ver patrones)
└─ Predicciones: Más precisas

SEMANA 3:
├─ 200 trades más
├─ Winrate: 65%
├─ Modelo: Bueno (aprende qué funciona)
└─ Predicciones: 70%+ accuracy

SEMANA 4:
├─ 200 trades más
├─ Winrate: 70%+
├─ Modelo: Excelente (es selectivo)
└─ Predicciones: 75%+ accuracy
```

## ✨ Resumen

✅ **Automático:** Se sincroniza en cada operación
✅ **Aprende:** El modelo mejora diariamente
✅ **Predice:** Cada trade tiene probabilidad de éxito
✅ **Mejora:** El winrate sube gradualmente
✅ **Flexible:** Puedes entrenar manual o automáticamente

---

**¡Sistema completo de IA + Trades en funcionamiento!** 🚀
