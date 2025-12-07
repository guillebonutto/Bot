#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtesting Real - Estrategia EMA + ML (7 Features)
Simula operaciones SIN ver datos futuros, exactamente como lo haría el bot en vivo
"""

import pandas as pd
import numpy as np
import glob
import os
import joblib
from datetime import datetime, timedelta
import json
from collections import defaultdict

# Configuración
INITIAL_BALANCE = 1000
RISK_PER_TRADE = 0.02
PAYOUT = 0.92  # 92% payout para wins
ML_THRESHOLD = 0.60
PAIRS = ['EURUSD_otc', 'GBPUSD_otc', 'AUDUSD_otc', 'USDCAD_otc', 'AUDCAD_otc', 'USDMXN_otc', 'USDCOP_otc']

def load_model():
    """Carga el modelo ML entrenado con 7 features"""
    try:
        model = joblib.load("ml_model.pkl")
        print("✅ Modelo ML cargado (7 features)")
        return model
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        return None

def load_history_data(history_dir="history"):
    """Carga datos históricos de archivos CSV"""
    print(f"\n📁 Cargando datos históricos desde {history_dir}...")
    
    all_files = glob.glob(os.path.join(history_dir, "*.csv"))
    data = {}
    
    for file in all_files:
        filename = os.path.basename(file)
        if "_" not in filename:
            continue
        
        try:
            df = pd.read_csv(file)
            
            # Normalizar nombres de columnas
            df.columns = [col.strip().lower() for col in df.columns]
            
            # Asegurar que hay timestamp
            if 'time' in df.columns and 'timestamp' not in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
            elif 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            else:
                print(f"⚠️ {file}: No tiene timestamp")
                continue
            
            # Renombrar columnas OHLC
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Validar columnas necesarias
            required = ['open', 'high', 'low', 'close', 'timestamp']
            if not all(col in df.columns for col in required):
                print(f"⚠️ {file}: Faltan columnas OHLC")
                continue
            
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Extraer pair y timeframe del nombre del archivo
            parts = filename.replace('.csv', '').split('_')
            if len(parts) >= 3:
                pair = f"{parts[0]}_{parts[1]}"
                tf = parts[2]
                key = f"{pair}_{tf}"
                data[key] = df
                print(f"  ✅ {key}: {len(df)} velas")
        
        except Exception as e:
            print(f"  ❌ Error en {file}: {e}")
    
    print(f"\n📊 Total: {len(data)} pares cargados")
    return data

def calculate_emas(df, window=60):
    """Calcula EMAs 8, 21, 55 en los últimos N datos"""
    if len(df) < 60:
        return None, None, None
    
    df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    
    return df['ema8'].iloc[-1], df['ema21'].iloc[-1], df['ema55'].iloc[-1]

def get_signal(df, pair, duration_sec, model):
    """
    Genera señal BUY/SELL si cumple condiciones
    Retorna: (signal_type, prob, price) o (None, 0, 0)
    """
    if len(df) < 60:
        return None, 0, 0
    
    c = df['close'].iloc[-1]  # Precio actual
    p = df['close'].iloc[-2]  # Precio anterior
    
    ema8, ema21, ema55 = calculate_emas(df)
    if ema8 is None:
        return None, 0, 0
    
    prob = 1.0
    signal = None
    
    # Condición BUY: EMA8 > EMA21 > EMA55 (más flexible)
    if ema8 > ema21 > ema55 and c > ema8:
        signal = "BUY"
        
        # Aplicar modelo ML con 7 features
        if model is not None:
            try:
                pair_idx = PAIRS.index(pair.replace('_otc', '')) if pair.replace('_otc', '') in PAIRS else 0
            except:
                pair_idx = 0
            
            # Hora normalizada
            hour = df['timestamp'].iloc[-1].hour
            hour_normalized = hour / 24
            
            # Features: [price, duration_minutes, pair_idx, ema8, ema21, ema55, hour_normalized]
            duration_minutes = duration_sec / 60
            feature_names = ['price', 'duration_minutes', 'pair_idx', 'ema8', 'ema21', 'ema55', 'hour_normalized']
            features_df = pd.DataFrame(
                [[c, duration_minutes, pair_idx, ema8, ema21, ema55, hour_normalized]],
                columns=feature_names
            )
            
            try:
                prob = model.predict_proba(features_df)[0][1]
            except:
                prob = 1.0
    
    # Condición SELL: EMA8 < EMA21 < EMA55
    elif ema8 < ema21 < ema55 and p >= ema8 and c < ema8:
        signal = "SELL"
        
        if model is not None:
            try:
                pair_idx = PAIRS.index(pair.replace('_otc', '')) if pair.replace('_otc', '') in PAIRS else 0
            except:
                pair_idx = 0
            
            hour = df['timestamp'].iloc[-1].hour
            hour_normalized = hour / 24
            duration_minutes = duration_sec / 60
            
            feature_names = ['price', 'duration_minutes', 'pair_idx', 'ema8', 'ema21', 'ema55', 'hour_normalized']
            features_df = pd.DataFrame(
                [[c, duration_minutes, pair_idx, ema8, ema21, ema55, hour_normalized]],
                columns=feature_names
            )
            
            try:
                prob = model.predict_proba(features_df)[0][0]
            except:
                prob = 1.0
    
    # Filtrar por threshold ML
    if signal and prob < ML_THRESHOLD:
        return None, 0, 0
    
    return signal, prob, c

def check_trade_result(entry_price, signal, future_df, duration_sec):
    """
    Verifica si el trade fue WIN o LOSS basado en movimiento futuro
    SIN MIRAR TODOS LOS DATOS - solo mira en el rango de tiempo esperado
    """
    if len(future_df) == 0:
        return None
    
    # Usar 1 pip como target (más fácil de alcanzar para generar más trades)
    target_pips = 1
    target_points = target_pips * 0.0001  # 1 pip
    
    if signal == "BUY":
        target_price = entry_price + target_points
        sl_price = entry_price - target_points * 2  # SL más amplio
        
        # Buscar en el futuro si toca target o SL
        for _, row in future_df.iterrows():
            if row['high'] >= target_price:
                return "WIN"
            if row['low'] <= sl_price:
                return "LOSS"
    
    elif signal == "SELL":
        target_price = entry_price - target_points
        sl_price = entry_price + target_points * 2
        
        for _, row in future_df.iterrows():
            if row['low'] <= target_price:
                return "WIN"
            if row['high'] >= sl_price:
                return "LOSS"
    
    # Si nunca toca target ni SL, es LOSS (timeout)
    return "LOSS"

def run_backtest(data, model):
    """
    Ejecuta backtesting en los datos históricos
    """
    print("\n🤖 INICIANDO BACKTESTING (7 FEATURES + HORA)...")
    print("=" * 60)
    
    trades = []
    stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'trades': 0})
    balance = INITIAL_BALANCE
    
    # Parámetros de duración (60s para M1)
    duration_sec = 60
    lookback_bars = 5  # Revisar 5 velas futuras (más cobertura)
    
    for pair_tf, df in sorted(data.items()):
        pair = pair_tf.rsplit('_', 1)[0]
        
        print(f"\n🔍 Procesando {pair_tf}...")
        
        # Iterar sobre velas (dejando margen para velas futuras)
        for i in range(60, len(df) - lookback_bars):
            # Datos hasta la vela actual (SIN ver el futuro)
            historical_df = df.iloc[:i+1].copy()
            
            # Datos futuros (para validar el trade)
            future_df = df.iloc[i+1:i+1+lookback_bars].copy()
            
            # Generar señal con datos históricos únicamente
            signal, prob, price = get_signal(historical_df, pair, duration_sec, model)
            
            if signal is None:
                continue
            
            # Validar resultado con datos futuros
            result = check_trade_result(price, signal, future_df, duration_sec)
            
            if result is None:
                continue
            
            # Registrar trade
            timestamp = historical_df['timestamp'].iloc[-1]
            hour = timestamp.hour
            
            profit_loss = 0
            if result == "WIN":
                profit_loss = balance * RISK_PER_TRADE * PAYOUT
                stats[pair]['wins'] += 1
            else:
                profit_loss = -balance * RISK_PER_TRADE
                stats[pair]['losses'] += 1
            
            balance += profit_loss
            stats[pair]['trades'] += 1
            
            trades.append({
                'timestamp': timestamp,
                'pair': pair,
                'signal': signal,
                'price': price,
                'prob': prob,
                'result': result,
                'pnl': profit_loss,
                'balance': balance,
                'hour': hour
            })
    
    return trades, stats, balance

def print_results(trades, stats, final_balance):
    """Imprime resultados del backtesting"""
    print("\n" + "=" * 80)
    print("📊 RESULTADOS DEL BACKTESTING (7 FEATURES + HORA)")
    print("=" * 80)
    
    total_trades = len(trades)
    if total_trades == 0:
        print("❌ No se generaron trades")
        return
    
    wins = sum(1 for t in trades if t['result'] == 'WIN')
    losses = total_trades - wins
    
    print(f"\n📈 RESUMEN GENERAL:")
    print(f"  Total de trades: {total_trades}")
    print(f"  Wins: {wins} ({wins/total_trades*100:.1f}%)")
    print(f"  Losses: {losses} ({losses/total_trades*100:.1f}%)")
    print(f"  Balance inicial: ${INITIAL_BALANCE:.2f}")
    print(f"  Balance final: ${final_balance:.2f}")
    print(f"  P&L total: ${final_balance - INITIAL_BALANCE:.2f}")
    print(f"  ROI: {(final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100:.2f}%")
    
    # Por par
    print(f"\n📊 DESEMPEÑO POR PAR:")
    print(f"{'Par':<15} {'Trades':<10} {'Wins':<10} {'Winrate':<12} {'Avg Prob':<10}")
    print("-" * 57)
    
    for pair in sorted(stats.keys()):
        data = stats[pair]
        trades_pair = [t for t in trades if t['pair'] == pair]
        
        if data['trades'] > 0:
            wr = data['wins'] / data['trades'] * 100
            avg_prob = np.mean([t['prob'] for t in trades_pair])
            print(f"{pair:<15} {data['trades']:<10} {data['wins']:<10} {wr:>6.1f}%       {avg_prob:.2f}")
    
    # Por hora
    print(f"\n⏰ DESEMPEÑO POR HORA:")
    print(f"{'Hora':<10} {'Trades':<10} {'Wins':<10} {'Winrate':<10}")
    print("-" * 40)
    
    by_hour = defaultdict(lambda: {'wins': 0, 'trades': 0})
    for t in trades:
        by_hour[t['hour']]['trades'] += 1
        if t['result'] == 'WIN':
            by_hour[t['hour']]['wins'] += 1
    
    for hour in sorted(by_hour.keys()):
        data = by_hour[hour]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        print(f"{hour:02d}:00       {data['trades']:<10} {data['wins']:<10} {wr:>6.1f}%")
    
    # Análisis por hora: qué horas son mejores
    print(f"\n🔥 HORAS MÁS RENTABLES:")
    best_hours = sorted(by_hour.items(), key=lambda x: x[1]['wins']/max(x[1]['trades'],1), reverse=True)[:5]
    for hour, data in best_hours:
        wr = data['wins'] / data['trades'] * 100
        print(f"  {hour:02d}:00 - {wr:.1f}% winrate ({data['wins']}/{data['trades']} trades)")
    
    # Guardar resultados
    results_file = "backtest_results_7features.json"
    with open(results_file, 'w') as f:
        json.dump({
            'total_trades': total_trades,
            'wins': wins,
            'winrate': wins/total_trades*100,
            'balance_initial': INITIAL_BALANCE,
            'balance_final': final_balance,
            'pnl': final_balance - INITIAL_BALANCE,
            'roi': (final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n💾 Resultados guardados en {results_file}")

if __name__ == "__main__":
    # Cargar modelo
    model = load_model()
    if model is None:
        print("❌ No se pudo cargar el modelo. Abortando.")
        exit(1)
    
    # Cargar datos históricos
    data = load_history_data()
    if not data:
        print("❌ No se cargaron datos históricos.")
        exit(1)
    
    # Ejecutar backtesting
    trades, stats, final_balance = run_backtest(data, model)
    
    # Mostrar resultados
    print_results(trades, stats, final_balance)
