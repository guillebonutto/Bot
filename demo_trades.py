"""
demo_trades.py
==============
Script para crear trades de ejemplo y probar el sistema de logging.
Útil para validar que el sistema funciona correctamente.
"""

from trade_logger import trade_logger
from datetime import datetime, timedelta, timezone
import random


def create_demo_trades(num_trades=20):
    """Crear trades de demostración."""
    
    pairs = ['EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc']
    timeframes = ['M5', 'M15', 'M30']
    patterns = ['Breakout', 'Compression', 'Flag', 'Triangle', 'Double Top']
    
    print(f"🤖 Creando {num_trades} trades de demostración...\n")
    
    now = datetime.now(timezone.utc)
    
    for i in range(num_trades):
        # Generar datos aleatorios
        pair = random.choice(pairs)
        tf = random.choice(timeframes)
        decision = random.choice(['BUY', 'SELL'])
        score = random.randint(1, 7)
        pattern = random.choice(patterns)
        price = random.uniform(1.0, 150.0)
        ema = price * random.uniform(0.98, 1.02)
        rsi = random.uniform(20, 80)
        
        trade_time = now - timedelta(hours=num_trades-i)
        
        # Registrar trade
        trade_id = f"DEMO{i+1:04d}"
        
        trade_logger.log_trade({
            'timestamp': trade_time,
            'trade_id': trade_id,
            'pair': pair,
            'timeframe': tf,
            'decision': decision,
            'signal_score': score,
            'pattern_detected': pattern,
            'price': price,
            'ema': ema,
            'rsi': rsi,
            'ema_conf': random.choice([-1, 0, 1]),
            'tf_signal': random.choice([-1, 0, 1]),
            'atr': random.uniform(0.0005, 0.005),
            'triangle_active': random.randint(0, 1),
            'reversal_candle': random.randint(0, 1),
            'near_support': random.choice([True, False]),
            'near_resistance': random.choice([True, False]),
            'support_level': price * 0.995,
            'resistance_level': price * 1.005,
            'htf_signal': random.choice([-1, 0, 1]),
            'result': 'PENDING',
            'expiry_time': random.choice([300, 900, 1800]),
        })
        
        print(f"✅ Trade {trade_id}: {decision} {pair} {tf} (Score: {score})")
    
    print(f"\n✅ {num_trades} trades creados")
    print(f"📁 Ubicación: logs/trades/trades_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv")
    print("\n🔍 Ahora puedes ejecutar:")
    print("   python analyze_trades.py --summary")
    print("   python analyze_trades.py --indicators")
    print("   python trades_dashboard.py")


def simulate_results():
    """Simular resultados de trades existentes."""
    df = trade_logger.get_todays_trades()
    
    if df.empty:
        print("❌ No hay trades para simular resultados")
        return
    
    print(f"\n📊 Simulando resultados para {len(df)} trades...\n")
    
    for _, trade in df.iterrows():
        if trade['result'] == 'PENDING':
            # 60% de ganancia, 40% de pérdida (sesgo positivo para demo)
            win = random.random() < 0.60
            result = 'WIN' if win else 'LOSS'
            
            # Calcular profit/loss (aproximado)
            amount = random.uniform(5, 20)  # Monto de la operación
            if win:
                profit = amount * random.uniform(0.8, 1.2)  # 80-120% de ganancia
            else:
                profit = None  # En pérdida no registramos el monto
            
            trade_logger.update_trade_result(
                trade['trade_id'],
                result=result,
                profit_loss=profit if win else None
            )
            
            icon = "✅" if win else "❌"
            print(f"{icon} {trade['trade_id']}: {result}")
    
    print("\n✅ Resultados simulados")
    print("📊 Ejecuta: python analyze_trades.py --summary")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--results':
        simulate_results()
    else:
        num = int(sys.argv[1]) if len(sys.argv) > 1 else 20
        create_demo_trades(num)
        print("\n💡 Para simular resultados, ejecuta:")
        print("   python demo_trades.py --results")
