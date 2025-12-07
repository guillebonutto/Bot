#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_ml_model.py
=================
Entrena un modelo ML con las MISMAS features que usa el bot
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib

print("=" * 60)
print("🤖 ENTRENAMIENTO DE MODELO ML (7 FEATURES + HORA)")
print("=" * 60)

# 1. Cargar todos los archivos de trades
trade_files = list(Path("logs/trades").glob("trades_*.csv"))
print(f"\n📁 Archivos encontrados: {len(trade_files)}")

all_trades = []
for file in trade_files:
    try:
        df = pd.read_csv(file)
        all_trades.append(df)
        print(f"  ✅ {file.name}: {len(df)} trades")
    except Exception as e:
        print(f"  ❌ {file.name}: Error - {e}")

if not all_trades:
    print("\n❌ No se encontraron datos de trades")
    exit(1)

# Combinar todos los trades
df_all = pd.concat(all_trades, ignore_index=True)
print(f"\n📊 Total de trades: {len(df_all)}")

# 2. Filtrar solo trades con resultado conocido
if 'result' not in df_all.columns:
    print("\n❌ No se encontró la columna 'result'")
    exit(1)

df_all = df_all[df_all['result'].notna()]
print(f"\n✅ Trades con resultado: {len(df_all)}")

# 3. Procesar timestamp para extraer hora
print(f"\n⏰ Procesando timestamp para extraer hora del día...")
if 'timestamp' in df_all.columns:
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
    df_all['hour'] = df_all['timestamp'].dt.hour
    df_all['hour_normalized'] = df_all['hour'] / 24  # Normalizar entre 0-1
    print(f"   ✅ Hora extraída (rango: {df_all['hour'].min()}-{df_all['hour'].max()})")
else:
    print(f"   ⚠️ No hay columna 'timestamp', usando hora aleatoria")
    df_all['hour'] = np.random.randint(0, 24, len(df_all))
    df_all['hour_normalized'] = df_all['hour'] / 24

# Calcular winrate
wins = (df_all['result'] == 'WIN').sum()
losses = (df_all['result'] == 'LOSS').sum()
winrate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
print(f"\n📈 Winrate actual: {winrate:.1f}% ({wins} wins / {losses} losses)")

# 4. Necesitamos calcular EMAs para cada trade
# Esto requiere datos históricos de candles
print(f"\n🔧 Calculando features con EMAs + HORA...")

# Verificar si tenemos las columnas necesarias
required_base_cols = ['price', 'pair', 'duration', 'result']
if not all(col in df_all.columns for col in required_base_cols):
    print(f"\n⚠️ Faltan columnas necesarias. Disponibles: {df_all.columns.tolist()}")
    print("   Usando features simplificados sin EMAs")
    
    # Features simplificados
    feature_cols = []
    if 'price' in df_all.columns:
        feature_cols.append('price')
    
    if 'duration' in df_all.columns:
        df_all['duration_minutes'] = df_all['duration'] / 60
        feature_cols.append('duration_minutes')
    elif 'timeframe' in df_all.columns:
        df_all['duration_minutes'] = df_all['timeframe'].str.extract(r'(\d+)').astype(float)
        feature_cols.append('duration_minutes')
    
    if 'pair' in df_all.columns:
        pairs = df_all['pair'].unique()
        pair_map = {pair: idx for idx, pair in enumerate(pairs)}
        df_all['pair_idx'] = df_all['pair'].map(pair_map)
        feature_cols.append('pair_idx')
    
    # Crear EMAs sintéticas (valores aleatorios para demostración)
    print("   ⚠️ Creando EMAs sintéticas (el modelo no será muy preciso)")
    df_all['ema8'] = df_all['price'] * (1 + np.random.uniform(-0.001, 0.001, len(df_all)))
    df_all['ema21'] = df_all['price'] * (1 + np.random.uniform(-0.002, 0.002, len(df_all)))
    df_all['ema55'] = df_all['price'] * (1 + np.random.uniform(-0.003, 0.003, len(df_all)))
    
    feature_cols.extend(['ema8', 'ema21', 'ema55'])
    
    # Agregar hora del día
    feature_cols.append('hour_normalized')

else:
    # Tenemos las columnas necesarias
    feature_cols = ['price', 'ema8', 'ema21', 'ema55', 'duration_minutes', 'pair_idx', 'hour_normalized']
    
    # Procesar duration
    if 'duration' in df_all.columns:
        df_all['duration_minutes'] = df_all['duration'] / 60
    
    # Procesar pair
    if 'pair' in df_all.columns:
        pairs = df_all['pair'].unique()
        pair_map = {pair: idx for idx, pair in enumerate(pairs)}
        df_all['pair_idx'] = df_all['pair'].map(pair_map)

print(f"  Features finales ({len(feature_cols)}): {feature_cols}")

# 4. Preparar datos para entrenamiento
X = df_all[feature_cols].fillna(0)
y = (df_all['result'] == 'WIN').astype(int)

print(f"\n📊 Datos de entrenamiento:")
print(f"  Features: {X.shape}")
print(f"  Labels: {y.shape}")
print(f"  Wins: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
print(f"  Losses: {len(y)-y.sum()} ({(len(y)-y.sum())/len(y)*100:.1f}%)")

if len(X) < 50:
    print(f"\n⚠️ Solo hay {len(X)} trades, se recomienda al menos 100")

# 5. Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n📊 Split de datos:")
print(f"  Train: {len(X_train)} samples")
print(f"  Test: {len(X_test)} samples")

# 6. Entrenar modelo
print(f"\n🤖 Entrenando Random Forest...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    class_weight='balanced'
)

model.fit(X_train, y_train)
print(f"  ✅ Modelo entrenado")

# 7. Evaluar modelo
print(f"\n📊 Evaluación en conjunto de prueba:")
y_pred = model.predict(X_test)
accuracy = (y_pred == y_test).mean()
print(f"  Accuracy: {accuracy*100:.1f}%")

print(f"\n📊 Reporte de clasificación:")
print(classification_report(y_test, y_pred, target_names=['LOSS', 'WIN']))

print(f"\n📊 Matriz de confusión:")
cm = confusion_matrix(y_test, y_pred)
print(f"  True Negatives (LOSS correctos): {cm[0,0]}")
print(f"  False Positives (predijo WIN, fue LOSS): {cm[0,1]}")
print(f"  False Negatives (predijo LOSS, fue WIN): {cm[1,0]}")
print(f"  True Positives (WIN correctos): {cm[1,1]}")

# 8. Feature importance
print(f"\n📊 Importancia de features:")
importances = model.feature_importances_
for feat, imp in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
    print(f"  {feat}: {imp:.3f}")

# 9. Guardar modelo
model_path = "ml_model.pkl"
joblib.dump(model, model_path)
print(f"\n💾 Modelo guardado en: {model_path}")

# 10. Guardar metadata
metadata = {
    'features': feature_cols,
    'n_samples': len(X),
    'accuracy': accuracy,
    'winrate': winrate,
    'trained_at': pd.Timestamp.now().isoformat()
}

import json
with open('ml_model_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\n✅ Metadata guardada en: ml_model_metadata.json")
print(f"\n{'='*60}")
print(f"🎉 ENTRENAMIENTO COMPLETADO")
print(f"{'='*60}")
print(f"\n💡 El bot ahora usará estas {len(feature_cols)} features:")
print(f"   {feature_cols}")
print(f"\n⚠️ IMPORTANTE: El bot debe pasar las features en este ORDEN:")
print(f"   features = [[price, ema8, ema21, ema55, duration/60, pair_idx, hour_normalized]]")
print(f"\n📍 LA HORA ahora es parte del entrenamiento:")
print(f"   - El modelo aprenderá qué horas son mejores para cada par")
print(f"   - Puede mejorar significativamente la probabilidad por horario")
