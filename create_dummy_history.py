"""
create_dummy_history.py
=======================
Crea históricos de prueba para desarrollo/testing sin necesidad de API.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta


def create_dummy_candles(pair: str, tf: str, count: int = 100) -> list:
    """
    Genera velas de prueba realistas.
    
    Args:
        pair: Par (EURUSD, GBPUSD, etc)
        tf: Timeframe (M5, M15, etc)
        count: Número de velas
    
    Returns:
        Lista de candles
    """
    candles = []
    
    # Precio inicial según par
    prices = {
        'EURUSD': 1.0850,
        'GBPUSD': 1.2700,
        'USDJPY': 150.50,
    }
    
    price = prices.get(pair, 1.0000)
    
    # Generar velas con movimiento realista
    now = datetime.now()
    
    for i in range(count, 0, -1):
        # Movimiento aleatorio pero realista (0.01% - 0.1%)
        change = random.uniform(-0.001, 0.001) * price
        
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) + abs(change) * 0.5
        low_price = min(open_price, close_price) - abs(change) * 0.5
        
        volume = random.randint(1000, 10000)
        
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
    print("🎲 CREANDO HISTÓRICOS DE PRUEBA")
    print("=" * 70)
    
    # Crear directorio
    history_dir = Path("history")
    history_dir.mkdir(exist_ok=True)
    
    pairs = {
        'EURUSD': ['M5', 'M15', 'M30'],
        'GBPUSD': ['M5', 'M15', 'M30'],
        'USDJPY': ['M5', 'M15', 'M30'],
    }
    
    total_files = 0
    
    for pair, timeframes in pairs.items():
        pair_dir = history_dir / pair
        pair_dir.mkdir(exist_ok=True)
        
        print(f"\n📊 {pair}:")
        
        for tf in timeframes:
            # Generar velas
            candles = create_dummy_candles(pair, tf, 100)
            
            # Guardar a JSON
            file_path = pair_dir / f"{tf}.json"
            with open(file_path, 'w') as f:
                json.dump({
                    'pair': pair,
                    'tf': tf,
                    'count': len(candles),
                    'timestamp': datetime.now().isoformat(),
                    'candles': candles
                }, f, indent=2)
            
            print(f"   ✅ {tf}: {len(candles)} velas guardadas")
            total_files += 1
    
    print(f"\n{'=' * 70}")
    print(f"✅ {total_files} archivos creados en: {history_dir.absolute()}")
    print(f"\n💡 Próximo paso: Ejecuta main.py")
    print(f"   python main.py")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
