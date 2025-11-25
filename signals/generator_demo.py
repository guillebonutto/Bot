"""
signals/generator_demo.py
=========================
Generador de señales en MODO DEMO - siempre retorna señales.
Usar para testear el bot sin problemas de indicadores.
"""

import asyncio
from config.constants import TIMEFRAMES
from utils.log import log
import numpy as np


async def generate_signal_demo(api, pair, tf):
    """
    Generador de señales DEMO - simula señales para testing.
    Retorna una señal cada vez, alternando BUY/SELL.
    
    Args:
        api: API instance
        pair: Par (EURUSD_otc, etc)
        tf: Timeframe (M5, M15, etc)
    
    Returns:
        Dict con señal o None
    """
    try:
        # Obtener datos para validar que existen
        interval = TIMEFRAMES.get(tf, 300)
        candles = await api.get_candles(pair, interval, 50)
        
        if not candles or len(candles) == 0:
            return None
        
        # Precio actual
        last_candle = candles[-1]
        price = float(last_candle.get('close', last_candle.get('Close', 0)))
        
        # Generar señal determinista basada en par+tf
        hash_val = hash(f"{pair}{tf}") % 100
        direction = 'BUY' if hash_val < 50 else 'SELL'
        
        # Retornar señal
        return {
            'pair': pair,
            'tf': tf,
            'signal': direction,
            'timestamp': last_candle.get('time', 0),
            'duration': interval,
            'score': 3,  # Score medio-bajo para pasar filtros
            'pattern': 'DEMO_MODE',
            'price': price,
            'ema': price * (1.002 if direction == 'BUY' else 0.998),
            'breakdown': {},
            'ema_conf': 1 if direction == 'BUY' else -1,
            'tf_score': 1,
            'rsi': 50,
            'triangle': 0,
            'reversal': 0,
            'near_resistance': False
        }
    
    except Exception as e:
        log(f"❌ Demo generator error {pair} {tf}: {e}", "debug")
        return None


async def generate_signal_with_semaphore(semaphore, api, pair, tf):
    """Wrapper con semaforo."""
    async with semaphore:
        try:
            return await generate_signal_demo(api, pair, tf)
        except Exception as e:
            log(f"⚠️ Exception en generate_signal_demo: {e}", "warning")
            return None
