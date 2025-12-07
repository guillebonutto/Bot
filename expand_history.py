#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generador de Datos Históricos Sintéticos
Expande los datos existentes con movimientos realistas basados en volatilidad y tendencias
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime, timedelta

def generate_realistic_candles(base_price, num_candles, volatility=0.001, trend=0):
    """
    Genera velas OHLC realistas basadas en:
    - Volatilidad (desviación estándar del movimiento)
    - Tendencia (drift positivo/negativo)
    """
    candles = []
    current_price = base_price
    
    for i in range(num_candles):
        # Movimiento de apertura
        open_price = current_price
        
        # Movimiento aleatorio con tendencia
        movement = np.random.normal(trend, volatility)
        close_price = open_price * (1 + movement)
        
        # High y Low con volatilidad intra-vela
        intra_volatility = volatility * 0.5
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, intra_volatility)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, intra_volatility)))
        
        # Volumen realista
        volume = np.random.randint(1000, 20000)
        
        candles.append({
            'open': round(open_price, 5),
            'close': round(close_price, 5),
            'high': round(high_price, 5),
            'low': round(low_price, 5),
            'volume': volume
        })
        
        current_price = close_price
    
    return candles

def expand_history_file(file_path, expansion_factor=5):
    """
    Lee un archivo de historial y lo expande multiplicando los datos
    """
    try:
        df = pd.read_csv(file_path)
        
        if len(df) == 0:
            print(f"⚠️ {file_path}: archivo vacío")
            return None
        
        # Convertir timestamps
        df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df = df.sort_values('timestamp')
        
        print(f"📂 Expandiendo {os.path.basename(file_path)}...")
        print(f"   Datos originales: {len(df)} velas")
        
        all_candles = df[['open', 'close', 'high', 'low', 'volume', 'timestamp']].to_dict('records')
        
        # Extraer volatilidad histórica
        returns = df['close'].pct_change()
        volatility = returns.std()
        
        # Generar nuevos datos futuros
        last_price = df['close'].iloc[-1]
        last_time = df['timestamp'].iloc[-1]
        
        # Generar múltiples bloques de datos sintéticos
        new_candles = []
        current_time = last_time
        current_price = last_price
        
        for block in range(expansion_factor):
            # Cada bloque tiene la misma cantidad de velas que el original
            synthetic = generate_realistic_candles(
                current_price, 
                len(df),
                volatility=volatility * 0.8,  # Usar volatilidad histórica como base
                trend=0.0001  # Pequeña tendencia alcista
            )
            
            for i, candle in enumerate(synthetic):
                current_time += timedelta(minutes=5)  # M5 = 5 minutos
                
                new_candles.append({
                    'open': candle['open'],
                    'close': candle['close'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'volume': candle['volume'],
                    'timestamp': current_time
                })
                
                current_price = candle['close']
        
        # Combinar datos originales + sintéticos
        original_df = pd.DataFrame(all_candles)
        synthetic_df = pd.DataFrame(new_candles)
        
        combined = pd.concat([original_df, synthetic_df], ignore_index=True)
        combined = combined.sort_values('timestamp').reset_index(drop=True)
        
        # Convertir timestamp a unix time para el formato original
        combined['time'] = combined['timestamp'].astype(int) // 10**9
        combined['id'] = range(len(combined), 0, -1)
        
        # Guardar con mismo formato
        output_df = combined[['id', 'open', 'close', 'high', 'low', 'volume', 'time']]
        output_df.to_csv(file_path, index=False)
        
        print(f"   ✅ Expandido a {len(output_df)} velas (x{expansion_factor})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return False

def main():
    history_dir = "history"
    expansion_factor = 10  # Multiplicar por 10 veces
    
    print("\n" + "=" * 60)
    print("🔧 EXPANSIÓN DE DATOS HISTÓRICOS")
    print("=" * 60)
    
    # Encontrar todos los archivos CSV
    csv_files = glob.glob(os.path.join(history_dir, "*.csv"))
    
    if not csv_files:
        print(f"❌ No se encontraron archivos CSV en {history_dir}")
        return
    
    print(f"\n📂 Encontrados {len(csv_files)} archivos de datos\n")
    
    success_count = 0
    for csv_file in sorted(csv_files):
        if expand_history_file(csv_file, expansion_factor):
            success_count += 1
    
    print(f"\n✅ {success_count}/{len(csv_files)} archivos expandidos exitosamente")
    print("\n💡 Ahora tienes ~1500 velas por timeframe para backtesting más robusto")
    print("=" * 60)

if __name__ == "__main__":
    main()
