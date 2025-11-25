"""
quick_test_signal.py
====================
Test rápido para verificar que genera señales.
"""

import asyncio
from signals.generator import generate_signal
from data.history_manager import HistoryManager
from config.bot_config import get_config
from config.constants import TIMEFRAMES


class MockAPI:
    def __init__(self, hm):
        self.hm = hm
    
    async def get_candles(self, pair, interval, count):
        return self.hm.get_candles(pair, interval, count)


async def test():
    config = get_config()
    hm = HistoryManager('history')
    hm.load_all(config.pairs, TIMEFRAMES)
    
    api = MockAPI(hm)
    
    print("\n" + "=" * 70)
    print("🧪 TEST DE GENERACIÓN DE SEÑALES")
    print("=" * 70 + "\n")
    
    # Test cada par y timeframe
    found = 0
    for pair in ['EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc']:
        for tf_name in ['M5', 'M15', 'M30']:
            try:
                signal = await generate_signal(api, pair, tf_name)
                if signal:
                    print(f"✅ {pair:12} {tf_name}: {signal['signal']:4} (score: {signal.get('score', 0)})")
                    found += 1
                else:
                    print(f"⏸️ {pair:12} {tf_name}: Sin señal")
            except Exception as e:
                print(f"❌ {pair:12} {tf_name}: Error - {str(e)[:50]}")
    
    print(f"\n{'=' * 70}")
    print(f"Resultado: {found} señales generadas")
    print(f"{'=' * 70}\n")
    
    if found > 0:
        print("✅ LISTO PARA EJECUTAR BOT")
        return True
    else:
        print("⚠️ Aún hay problemas")
        return False


if __name__ == "__main__":
    result = asyncio.run(test())
    exit(0 if result else 1)
