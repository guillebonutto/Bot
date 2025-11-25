"""
test_signal_generation.py
=========================
Prueba la generación de señales con los históricos creados.
"""

import asyncio
import json
from pathlib import Path
from data.history_manager import HistoryManager
from analysis.scoring import SignalScorer
from signals.generator import generate_signal
from config.bot_config import get_config
from config.constants import TIMEFRAMES
from utils.log import log


async def test_signals():
    """Prueba generación de señales."""
    log("=" * 70)
    log("🧪 PRUEBA DE GENERACIÓN DE SEÑALES")
    log("=" * 70)
    
    config = get_config()
    
    # Cargar históricos
    log("\n📚 Cargando históricos...")
    history_manager = HistoryManager("history")
    history_manager.load_all(config.pairs, TIMEFRAMES)
    
    log(f"✅ Históricos cargados")
    
    # Simular API con históricos cargados (mock)
    class MockAPI:
        def __init__(self, history_mgr):
            self.history_mgr = history_mgr
        
        async def get_candles(self, pair, interval, count=100):
            return self.history_mgr.get_candles(pair, interval, count)
    
    api = MockAPI(history_manager)
    
    # Probar generación de señales
    log("\n🔍 Generando señales...")
    log(f"   Pares: {config.pairs}")
    log(f"   TF: {config.selected_tfs}\n")
    
    signals_found = []
    
    for pair in config.pairs:
        for tf in config.selected_tfs:
            try:
                signal = await generate_signal(api, pair, tf)
                
                if signal:
                    signals_found.append((pair, tf, signal))
                    log(f"✅ {pair} {tf}: {signal}")
                else:
                    log(f"⏸️ {pair} {tf}: Sin señal")
            
            except Exception as e:
                log(f"❌ {pair} {tf}: Error - {e}")
    
    log(f"\n{'=' * 70}")
    if signals_found:
        log(f"✅ Total: {len(signals_found)} señales generadas")
        for pair, tf, sig in signals_found:
            log(f"   • {pair} {tf}: {sig.get('signal', 'N/A')} (score: {sig.get('score', 0)})")
    else:
        log(f"⚠️ No se generaron señales")
        log(f"\n   Causas posibles:")
        log(f"   1. Datos insuficientes (necesita MA_LONG velas)")
        log(f"   2. Indicadores no confirman (RSI, EMA, etc)")
        log(f"   3. Score mínimo muy alto")
    
    log(f"{'=' * 70}\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_signals())
    except Exception as e:
        log(f"❌ Error: {e}", "error")
        import traceback
        traceback.print_exc()
