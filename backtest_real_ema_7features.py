#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtesting con Datos Reales - EMA Pullback Strategy
Analiza los trades ejecutados realmente y calcula performance del nuevo modelo (7 features + hora)
"""

import pandas as pd
import numpy as np
import glob
import os
import joblib
from datetime import datetime
import json
from collections import defaultdict

# Configuración
PAIRS_TARGET = ['EURUSD_otc', 'GBPUSD_otc', 'AUDUSD_otc', 'USDCAD_otc', 'AUDCAD_otc', 'USDMXN_otc', 'USDCOP_otc']
ML_THRESHOLD = 0.60

def load_model():
    """Carga el modelo ML entrenado con 7 features"""
    try:
        model = joblib.load("ml_model.pkl")
        print("✅ Modelo ML cargado (7 features)")
        return model
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        return None

def load_trade_logs():
    """Carga los trades reales ejecutados"""
    print("\n📂 Cargando logs de trades reales...")
    
    all_files = glob.glob("logs/trades/trades_*.csv")
    
    if not all_files:
        print("❌ No se encontraron logs de trades")
        return None
    
    dfs = []
    for file in sorted(all_files):
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ Error leyendo {file}: {e}")
    
    if not dfs:
        return None
    
    all_trades = pd.concat(dfs, ignore_index=True)
    
    # Convertir timestamp
    all_trades['timestamp'] = pd.to_datetime(all_trades['timestamp'])
    
    # Filtrar por patrón (EMA Pullback)
    if 'pattern_detected' in all_trades.columns:
        all_trades = all_trades[all_trades['pattern_detected'].str.contains('EMA', case=False, na=False)]
    
    # Filtrar por pares objetivo
    all_trades = all_trades[all_trades['pair'].isin(PAIRS_TARGET)]
    
    # Filtrar solo trades completados (WIN/LOSS)
    all_trades = all_trades[all_trades['result'].isin(['WIN', 'LOSS'])]
    
    if len(all_trades) == 0:
        print("⚠️ No hay trades de EMA Pullback en los logs")
        return None
    
    print(f"✅ Cargados {len(all_trades)} trades reales (EMA Pullback)")
    print(f"   Pares: {all_trades['pair'].unique()}")
    print(f"   Fecha: {all_trades['timestamp'].min()} a {all_trades['timestamp'].max()}")
    
    return all_trades

def extract_features_from_trade(row):
    """Extrae features de una fila de trade para pasar al modelo"""
    try:
        pair = row['pair']
        pair_idx = PAIRS_TARGET.index(pair) if pair in PAIRS_TARGET else 0
        
        # Extraer hora
        timestamp = pd.to_datetime(row['timestamp'])
        hour = timestamp.hour
        hour_normalized = hour / 24
        
        # Extraer duración en minutos
        duration = row.get('expiry_time', 300)  # Default 5 minutos
        duration_minutes = duration / 60
        
        # Extraer precios y EMAs
        price = row.get('price', 0)
        ema8 = row.get('ema', 0)  # En los logs es 'ema' genérico
        ema21 = row.get('ema', 0)  # Usar mismo valor si no hay separación
        ema55 = row.get('ema', 0)
        
        features = {
            'price': price,
            'duration_minutes': duration_minutes,
            'pair_idx': pair_idx,
            'ema8': ema8,
            'ema21': ema21,
            'ema55': ema55,
            'hour_normalized': hour_normalized
        }
        
        return features
    except Exception as e:
        print(f"⚠️ Error extrayendo features: {e}")
        return None

def apply_ml_model(trades_df, model):
    """
    Aplica el modelo ML a los trades reales
    Calcula qué trades habría rechazado/aceptado el nuevo modelo
    """
    print("\n🤖 Aplicando modelo ML a trades reales...")
    
    trades_with_ml = []
    
    for idx, row in trades_df.iterrows():
        features = extract_features_from_trade(row)
        
        if features is None:
            continue
        
        # Crear DataFrame con nombres de features
        feature_names = ['price', 'duration_minutes', 'pair_idx', 'ema8', 'ema21', 'ema55', 'hour_normalized']
        features_df = pd.DataFrame([features], columns=feature_names)
        
        # Obtener predicción del modelo
        try:
            # Para BUY
            if row.get('decision', '').upper() == 'BUY':
                prob = model.predict_proba(features_df)[0][1]
            # Para SELL
            else:
                prob = model.predict_proba(features_df)[0][0]
        except:
            prob = 0.5
        
        # Determinar si el modelo habría aceptado o rechazado
        would_accept = prob >= ML_THRESHOLD
        
        trade_data = row.to_dict()
        trade_data['ml_prob'] = prob
        trade_data['ml_would_accept'] = would_accept
        trade_data['hour'] = pd.to_datetime(row['timestamp']).hour
        
        trades_with_ml.append(trade_data)
    
    return pd.DataFrame(trades_with_ml)

def analyze_results(trades_df):
    """Analiza los resultados del backtesting"""
    print("\n" + "=" * 80)
    print("📊 ANÁLISIS DE TRADES REALES CON MODELO ML (7 FEATURES + HORA)")
    print("=" * 80)
    
    total_trades = len(trades_df)
    
    if total_trades == 0:
        print("❌ No hay trades para analizar")
        return
    
    # Estadísticas globales
    actual_wins = (trades_df['result'] == 'WIN').sum()
    actual_losses = (trades_df['result'] == 'LOSS').sum()
    actual_winrate = actual_wins / total_trades * 100
    
    # Estadísticas con modelo ML
    accepted_trades = trades_df[trades_df['ml_would_accept']]
    accepted_wins = (accepted_trades['result'] == 'WIN').sum()
    accepted_losses = (accepted_trades['result'] == 'LOSS').sum()
    
    if len(accepted_trades) > 0:
        accepted_winrate = accepted_wins / len(accepted_trades) * 100
    else:
        accepted_winrate = 0
    
    rejected_trades = trades_df[~trades_df['ml_would_accept']]
    rejected_losses = (rejected_trades['result'] == 'LOSS').sum()
    
    print(f"\n📈 RESUMEN GENERAL:")
    print(f"  Total de trades reales: {total_trades}")
    print(f"  Wins reales: {actual_wins} ({actual_winrate:.1f}%)")
    print(f"  Losses reales: {actual_losses} ({actual_losses/total_trades*100:.1f}%)")
    
    print(f"\n🤖 CON MODELO ML (7 FEATURES):")
    print(f"  Trades aceptados: {len(accepted_trades)} ({len(accepted_trades)/total_trades*100:.1f}%)")
    print(f"  Trades rechazados: {len(rejected_trades)} ({len(rejected_trades)/total_trades*100:.1f}%)")
    
    if len(accepted_trades) > 0:
        print(f"  Winrate (aceptados): {accepted_winrate:.1f}%")
        print(f"  Mejora: {accepted_winrate - actual_winrate:+.1f}pp")
    
    if len(rejected_trades) > 0:
        print(f"\n  Trades rechazados que fueron LOSS: {rejected_losses}/{len(rejected_trades)}")
        print(f"  → Habrían evitado: {rejected_losses} trades malos")
    
    # Por par
    print(f"\n📊 DESEMPEÑO POR PAR (TRADES ACEPTADOS):")
    print(f"{'Par':<15} {'Trades':<10} {'Wins':<10} {'Winrate':<12} {'Avg Prob':<10}")
    print("-" * 57)
    
    for pair in PAIRS_TARGET:
        pair_trades = accepted_trades[accepted_trades['pair'] == pair]
        
        if len(pair_trades) > 0:
            wins = (pair_trades['result'] == 'WIN').sum()
            wr = wins / len(pair_trades) * 100
            avg_prob = pair_trades['ml_prob'].mean()
            print(f"{pair:<15} {len(pair_trades):<10} {wins:<10} {wr:>6.1f}%       {avg_prob:.2f}")
    
    # Por hora
    print(f"\n⏰ DESEMPEÑO POR HORA (TRADES ACEPTADOS):")
    print(f"{'Hora':<10} {'Trades':<10} {'Wins':<10} {'Winrate':<10}")
    print("-" * 40)
    
    by_hour = defaultdict(lambda: {'wins': 0, 'trades': 0})
    for idx, row in accepted_trades.iterrows():
        by_hour[row['hour']]['trades'] += 1
        if row['result'] == 'WIN':
            by_hour[row['hour']]['wins'] += 1
    
    for hour in sorted(by_hour.keys()):
        data = by_hour[hour]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        print(f"{hour:02d}:00       {data['trades']:<10} {data['wins']:<10} {wr:>6.1f}%")
    
    # Mejores horas
    if by_hour:
        print(f"\n🔥 HORAS MÁS RENTABLES (TRADES ACEPTADOS):")
        best_hours = sorted(by_hour.items(), 
                          key=lambda x: x[1]['wins']/max(x[1]['trades'],1), 
                          reverse=True)[:5]
        for hour, data in best_hours:
            wr = data['wins'] / data['trades'] * 100
            print(f"  {hour:02d}:00 - {wr:.1f}% winrate ({data['wins']}/{data['trades']} trades)")
    
    # Guardar resultados
    results_file = "backtest_real_7features_analysis.json"
    with open(results_file, 'w') as f:
        json.dump({
            'total_real_trades': total_trades,
            'real_wins': int(actual_wins),
            'real_winrate': actual_winrate,
            'ml_accepted_trades': len(accepted_trades),
            'ml_accepted_wins': int(accepted_wins),
            'ml_accepted_winrate': accepted_winrate,
            'ml_rejected_trades': len(rejected_trades),
            'bad_trades_avoided': int(rejected_losses),
            'winrate_improvement': accepted_winrate - actual_winrate,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n💾 Resultados guardados en {results_file}")

if __name__ == "__main__":
    # Cargar modelo
    model = load_model()
    if model is None:
        print("❌ No se pudo cargar el modelo. Abortando.")
        exit(1)
    
    # Cargar trades reales
    trades_df = load_trade_logs()
    if trades_df is None:
        print("❌ No se cargaron trades reales.")
        exit(1)
    
    # Aplicar modelo ML
    trades_with_ml = apply_ml_model(trades_df, model)
    
    # Analizar resultados
    analyze_results(trades_with_ml)
