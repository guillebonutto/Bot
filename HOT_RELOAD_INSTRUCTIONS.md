# Instrucciones para integrar hot-reload en bot_ema_pullback.py

## 1. Reemplazar la sección de carga del modelo (líneas 62-70)

### ANTES:
```python
try:
    import joblib
    model = joblib.load("ml_model.pkl")
    ML_ACTIVE = True
    ML_THRESHOLD = 0.62
    print("Modelo ML cargado")
except:
    ML_ACTIVE = False
    print("Sin modelo ML")
```

### DESPUÉS:
```python
# Importar el gestor de modelos con hot-reload
from ml_model_manager import ml_manager

ML_ACTIVE = ml_manager.is_active()
ML_THRESHOLD = ml_manager.get_threshold()
```

## 2. Actualizar get_signal() para usar el gestor (líneas 96-97 y 117-118)

### ANTES (línea 96-97):
```python
features = [[c, e8, e21, e55, duration/60, pair_idx]]
prob = model.predict_proba(features)[0][1]
```

### DESPUÉS:
```python
features = [[c, e8, e21, e55, duration/60, pair_idx]]
prob_result = ml_manager.predict_proba(features)
if prob_result is None:
    return None
prob = prob_result[0][1]
```

### ANTES (línea 117-118):
```python
features = [[c, e8, e21, e55, duration/60, pair_idx]]
prob = model.predict_proba(features)[0][0]
```

### DESPUÉS:
```python
features = [[c, e8, e21, e55, duration/60, pair_idx]]
prob_result = ml_manager.predict_proba(features)
if prob_result is None:
    return None
prob = prob_result[0][0]
```

## 3. Actualizar la variable ML_ACTIVE en el loop principal

Agregar al inicio del loop principal (después de la línea 143):

```python
# Actualizar estado del ML
ML_ACTIVE = ml_manager.is_active()
```

## Beneficios

✅ **Hot-Reload Automático:** El modelo se recarga cada 10 segundos si detecta cambios
✅ **Auto-Entrenamiento:** Se re-entrena automáticamente cada 24 horas
✅ **Thread-Safe:** Usa locks para evitar race conditions
✅ **Sin Reinicio:** El bot sigue funcionando mientras el modelo se actualiza

## Configuración

Para cambiar el intervalo de auto-entrenamiento, editar `ml_model_manager.py`:

```python
ml_manager = MLModelManager(
    auto_train_enabled=True,
    auto_train_interval_hours=12  # Cambiar a 12 horas, por ejemplo
)
```
