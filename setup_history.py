"""
setup_history.py
================
Descarga y almacena históricos de velas necesarios para el bot.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
from utils.log import log


async def download_history(ssid: str):
    """
    Descarga históricos para todos los pares configurados.
    
    Args:
        ssid: SSID válido de PocketOption
    """
    log("=" * 70)
    log("📚 DESCARGANDO HISTÓRICOS")
    log("=" * 70)
    
    # Crear directorio
    history_dir = Path("history")
    history_dir.mkdir(exist_ok=True)
    
    # Pares y timeframes
    pairs = ['EURUSD_otc', 'GBPUSD_otc', 'USDJPY_otc']
    timeframes = ['M5', 'M10', 'M15', 'M30', 'H1']
    
    # Inicializar API
    api = PocketOptionAsync(ssid=ssid)
    
    try:
        balance = await api.balance()
        log(f"✅ Conectado. Balance: ${balance:.2f}\n")
        
        # Para cada par
        for pair in pairs:
            log(f"\n📊 Descargando {pair}...")
            pair_dir = history_dir / pair.replace('_otc', '')
            pair_dir.mkdir(exist_ok=True)
            
            # Para cada timeframe
            for tf in timeframes:
                try:
                    log(f"  ⏱️  {tf}...", end="")
                    
                    # Descargar velas (últimas 100)
                    candles = await api.get_candles(pair, tf, 100)
                    
                    if candles and len(candles) > 0:
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
                        
                        log(f" ✅ {len(candles)} velas")
                    else:
                        log(f" ⚠️  Sin datos")
                    
                    # Delay para evitar rate limiting
                    await asyncio.sleep(2)
                
                except Exception as e:
                    log(f" ❌ Error: {e}")
                    await asyncio.sleep(3)
        
        log(f"\n{'=' * 70}")
        log(f"✅ Históricos descargados a: {history_dir.absolute()}")
        log(f"{'=' * 70}\n")
        
    except Exception as e:
        log(f"❌ Error: {e}", "error")


async def main():
    print("\n" + "=" * 70)
    print("📚 SETUP DE HISTÓRICOS")
    print("=" * 70)
    
    ssid = input("\nIntroduce tu SSID: ").strip()
    if not ssid:
        log("❌ SSID requerido", "error")
        return
    
    await download_history(ssid)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n⚠️ Cancelado por usuario", "warning")
    except Exception as e:
        log(f"❌ Error: {e}", "error")
