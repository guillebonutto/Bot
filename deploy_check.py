#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 DEPLOYMENT CHECKER - Bot EMA Pullback (7 Features)
Verifica que todo esté listo antes de desplegar el bot en vivo
"""

import os
import sys
import json
import joblib
from datetime import datetime
from pathlib import Path

def check_environment():
    """Verifica variables de entorno"""
    print("\n✅ VERIFICANDO VARIABLES DE ENTORNO")
    print("=" * 60)
    
    required_vars = {
        'POCKETOPTION_SSID': 'Credenciales PocketOption',
        'TELEGRAM_TOKEN': 'Token Telegram',
        'TELEGRAM_CHAT_ID': 'Chat ID Telegram'
    }
    
    missing = []
    for var, desc in required_vars.items():
        if os.getenv(var):
            print(f"  ✅ {var}: Configurado ({desc})")
        else:
            print(f"  ❌ {var}: FALTA ({desc})")
            missing.append(var)
    
    return len(missing) == 0

def check_model():
    """Verifica que el modelo ML está disponible"""
    print("\n✅ VERIFICANDO MODELO ML")
    print("=" * 60)
    
    if not os.path.exists("ml_model.pkl"):
        print("  ❌ ml_model.pkl no encontrado")
        return False
    
    try:
        model = joblib.load("ml_model.pkl")
        print("  ✅ Modelo ML cargado correctamente")
        print(f"     Tipo: {type(model).__name__}")
        
        # Verificar que tiene 7 features
        n_features = model.n_features_in_
        print(f"     Features: {n_features}")
        
        if n_features != 7:
            print(f"  ❌ Esperado 7 features pero tiene {n_features}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Error cargando modelo: {e}")
        return False

def check_metadata():
    """Verifica metadata del modelo"""
    print("\n✅ VERIFICANDO METADATA")
    print("=" * 60)
    
    if not os.path.exists("ml_model_metadata.json"):
        print("  ❌ ml_model_metadata.json no encontrado")
        return False
    
    try:
        with open("ml_model_metadata.json", 'r') as f:
            metadata = json.load(f)
        
        print(f"  ✅ Metadata cargada")
        print(f"     Fecha entrenamiento: {metadata.get('training_date', 'N/A')}")
        print(f"     Trades usados: {metadata.get('total_trades', 'N/A')}")
        print(f"     Accuracy: {metadata.get('accuracy', 'N/A')}")
        print(f"     Features: {metadata.get('feature_names', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error cargando metadata: {e}")
        return False

def check_trade_logger():
    """Verifica que el sistema de logging de trades funciona"""
    print("\n✅ VERIFICANDO SISTEMA DE LOGGING")
    print("=" * 60)
    
    try:
        from trade_logger import trade_logger
        print("  ✅ Trade logger importado correctamente")
        
        # Verificar que existe el directorio de logs
        if not os.path.exists("logs/trades"):
            os.makedirs("logs/trades", exist_ok=True)
            print("  ✅ Directorio logs/trades creado")
        
        # Verificar últimos logs
        import glob
        files = glob.glob("logs/trades/trades_*.csv")
        if files:
            latest = sorted(files)[-1]
            print(f"  ✅ Último log: {os.path.basename(latest)}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error con trade logger: {e}")
        return False

def check_telegram():
    """Verifica conectividad con Telegram"""
    print("\n✅ VERIFICANDO TELEGRAM")
    print("=" * 60)
    
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("  ⚠️  Token o Chat ID faltando")
        return False
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"  ✅ Token válido")
                print(f"     Bot: {data['result']['first_name']}")
                return True
        
        print(f"  ❌ Token inválido (code: {response.status_code})")
        return False
    
    except Exception as e:
        print(f"  ⚠️  No se pudo verificar Telegram: {e}")
        return True  # No es fatal

def check_backtesting():
    """Verifica resultados de backtesting"""
    print("\n✅ VERIFICANDO BACKTESTING")
    print("=" * 60)
    
    if os.path.exists("backtest_real_7features_analysis.json"):
        try:
            with open("backtest_real_7features_analysis.json", 'r') as f:
                results = json.load(f)
            
            print(f"  ✅ Análisis de backtesting disponible")
            print(f"     Trades reales: {results.get('total_real_trades', 'N/A')}")
            print(f"     Winrate actual: {results.get('real_winrate', 0):.1f}%")
            print(f"     Winrate con modelo: {results.get('ml_accepted_winrate', 0):.1f}%")
            print(f"     Mejora: {results.get('winrate_improvement', 0):+.1f}pp")
            
            return True
        except Exception as e:
            print(f"  ⚠️  Error leyendo backtesting: {e}")
            return True  # No es fatal
    
    print("  ⚠️  No hay resultados de backtesting reciente")
    return True  # No es fatal

def main():
    print("\n" + "=" * 60)
    print("🚀 DEPLOYMENT CHECKER - BOT EMA PULLBACK (7 FEATURES)")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checks = [
        ("Entorno", check_environment),
        ("Modelo ML", check_model),
        ("Metadata", check_metadata),
        ("Logging", check_trade_logger),
        ("Telegram", check_telegram),
        ("Backtesting", check_backtesting),
    ]
    
    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"  ❌ Error en {name}: {e}")
            results.append((name, False))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    all_pass = all(result for _, result in results)
    
    if all_pass:
        print("\n" + "=" * 60)
        print("✅ TODO LISTO PARA DESPLEGAR")
        print("=" * 60)
        print("\n🚀 Para iniciar el bot, ejecuta:")
        print("   python bots/bot_ema_pullback.py")
        print("\n📊 Para monitorear, usa los comandos Telegram:")
        print("   /balance - Ver balance actual")
        print("   /info - Resumen de trades")
        print("   /commands - Ver todos los comandos")
        print("\n💡 El bot usará:")
        print("   - 7 features (price, duration, pair_idx, ema8, ema21, ema55, hour_normalized)")
        print("   - Threshold ML: 60%")
        print("   - Pares: 7 (EURUSD, GBPUSD, AUDUSD, USDCAD, AUDCAD, USDMXN, USDCOP)")
        print("   - Timeframes: M1, M5")
        print("\n⚠️  IMPORTANTE:")
        print("   - Revisa que POCKETOPTION_SSID sea válido")
        print("   - El bot operará automáticamente cada 7 segundos")
        print("   - Monitorea en Telegram para alertas en tiempo real")
        return 0
    
    else:
        print("\n" + "=" * 60)
        print("❌ FALLOS DETECTADOS - NO SE PUEDE DESPLEGAR")
        print("=" * 60)
        print("\nFija los siguientes problemas antes de continuar:")
        for name, result in results:
            if not result:
                print(f"  - {name}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
