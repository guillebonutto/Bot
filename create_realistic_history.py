"""
create_realistic_history.py
============================
Crea históricos con tendencias claras para generar señales.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta


def create_trending_candles(pair: str, tf: str, count: int = 100, trend: str = 'up') -> list:
    """
    Genera velas con tendencia clara para que genere señales.
    
    Args:
        pair: Par (EURUSD, GBPUSD, etc)
        tf: Timeframe (M5, M15, etc)
        count: Número de velas
        trend: 'up', 'down', o 'mixed'
    """
    candles = []
    
    prices = {
        'EURUSD': 1.0850,
        'GBPUSD': 1.2700,
        'USDJPY': 150.50,
    }
    
    price = prices.get(pair, 1.0000)
    
    # Generar con tendencia CLARA
    now = datetime.now()
    
    for i in range(count, 0, -1):
        # Movimiento más pronunciado y direccional
        if trend == 'up':
            change = random.uniform(0.0005, 0.002) * price  # 0.05% - 0.2% UP
        elif trend == 'down':
            change = random.uniform(-0.002, -0.0005) * price  # 0.05% - 0.2% DOWN
        else:  # mixed
            change = random.uniform(-0.002, 0.002) * price
        
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) * 1.001  # Pequeño rango
        low_price = min(open_price, close_price) * 0.999
        
        volume = random.randint(5000, 20000)
        
        candle = {
            'id': i,
            'open': round(open_price, 5),
            'close': round(close_price, 5),
            'high': round(high_price, 5),
            'low': round(low_price, 5),
            'volume': volume,
            'time': int((now - timedelta(minutes=5*i)).timestamp())
        }
        
        candles.append(candle)
        price = close_price
    
    return candles


def main():
    print("\n" + "=" * 70)
    print("🚀 CREANDO HISTÓRICOS CON TENDENCIAS")
    print("=" * 70)
    
    history_dir = Path("history")
    history_dir.mkdir(exist_ok=True)
    
    # Configuración: pair -> [tendencia por timeframe]
    pairs_config = {
        'EURUSD': {'M5': 'up', 'M15': 'up', 'M30': 'up'},       # Tendencia ALCISTA fuerte
        'GBPUSD': {'M5': 'down', 'M15': 'down', 'M30': 'down'}, # Tendencia BAJISTA
        'USDJPY': {'M5': 'mixed', 'M15': 'up', 'M30': 'up'},     # Mixto en M5, alcista en otros
    }
    
    total_files = 0
    
    for pair, tfs_config in pairs_config.items():
        pair_dir = history_dir / pair
        pair_dir.mkdir(exist_ok=True)
        
        print(f"\n📊 {pair}:")
        
        for tf, trend in tfs_config.items():
            # Generar velas con tendencia
            candles = create_trending_candles(pair, tf, 150, trend)  # Más velas
            
            # Guardar JSON
            json_file = pair_dir / f"{tf}.json"
            with open(json_file, 'w') as f:
                json.dump({
                    'pair': pair,
                    'tf': tf,
                    'count': len(candles),
                    'trend': trend,
                    'timestamp': datetime.now().isoformat(),
                    'candles': candles
                }, f, indent=2)
            
            print(f"   ✅ {tf}: {len(candles)} velas ({trend.upper()})")
            total_files += 1
    
    print(f"\n{'=' * 70}")
    print(f"✅ {total_files} archivos creados con tendencias claras")
    print(f"\n📝 Próximo: Convertir a CSV")
    print(f"   python convert_json_to_csv.py")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
