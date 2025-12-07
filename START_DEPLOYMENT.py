#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
╔════════════════════════════════════════════════════════════════════════╗
║                  🚀 BOT TRADING EMA PULLBACK (7 FEATURES)              ║
║                         READY FOR DEPLOYMENT                           ║
╚════════════════════════════════════════════════════════════════════════╝

## QUICK START

### 1️⃣  OBTENER CREDENCIALES (5 min)

  PocketOption SSID:
  ────────────────────
  1. Ve a https://pocketoption.com
  2. Inicia sesión
  3. DevTools (F12) → Application → Cookies → "ssid"
  4. Copia el valor (string largo)
  
  Telegram Token:
  ────────────────────
  1. Abre Telegram
  2. Busca @BotFather
  3. /newbot → Elige nombre → Copia TOKEN
  
  Telegram Chat ID:
  ────────────────────
  1. Escribe mensaje a tu bot
  2. https://api.telegram.org/bot{TOKEN}/getUpdates
  3. Busca "id":12345678 → ESE es tu CHAT_ID

### 2️⃣  CONFIGURAR .env (1 min)

  Abre .env y reemplaza:
  ────────────────────
  POCKETOPTION_SSID=tu_ssid_aqui
  TELEGRAM_TOKEN=tu_token_aqui
  TELEGRAM_CHAT_ID=tu_chat_id_aqui

### 3️⃣  VERIFICAR (1 min)

  python deploy_check.py
  
  Debería mostrar: ✅ TODO LISTO PARA DESPLEGAR

### 4️⃣  INICIAR BOT (1 min)

  python bots/bot_ema_pullback.py
  
  El bot operará automáticamente. 
  Monitorea en Telegram para alertas.

─────────────────────────────────────────────────────────────────────────

## 📊 RESUMEN TÉCNICO

Feature Engineering:
  ✅ 6 features → 7 features (+ hour_normalized)
  ✅ Modelo reentrenado: 63.4% accuracy
  ✅ Backtesting real: 56% winrate (+5.9pp)

Backtesting Results:
  ✅ 758 trades reales analizados
  ✅ 116 aceptados (15.3% - muy selectivo)
  ✅ 327 trades malos evitados
  
Performance por Par:
  🥇 USDMXN: 75% winrate (28 trades)
  🥈 USDCAD: 60% winrate (25 trades)
  🥉 AUDUSD: 49% winrate (51 trades)

Horas Óptimas:
  ⭐ 01:00-04:00 (80% winrate)
  ⭐ 12:00, 17:00 (80-100% winrate)
  ❌ 07:00, 10:00, 20:00 (evitar)

─────────────────────────────────────────────────────────────────────────

## 🎮 COMANDOS TELEGRAM (mientras bot está corriendo)

  /balance         → Ver balance actual
  /info            → Resumen de trades
  /info_details    → Detalles por fecha
  /range_stats     → Estadísticas por hora
  /commands        → Ayuda de comandos

─────────────────────────────────────────────────────────────────────────

## ⚠️  IMPORTANTE

  ✅ Revisa que SSID sea válido (expira después de horas)
  ✅ Token Telegram debe ser del bot correcto
  ✅ El bot operará automáticamente cada 7 segundos
  ✅ Risk management: 1% del balance por trade
  ✅ Monitorea en Telegram para errores

─────────────────────────────────────────────────────────────────────────

## 📖 DOCUMENTACIÓN COMPLETA

  Ver estos archivos para más detalles:
  
  - DEPLOYMENT_GUIDE.md      → Guía completa step-by-step
  - PROJECT_SUMMARY.md       → Resumen técnico del proyecto
  - deploy_check.py          → Verificación automática
  - backtest_real_ema_7features.py → Análisis de backtesting

─────────────────────────────────────────────────────────────────────────

## 🔧 TROUBLESHOOTING

  "SSID invalid"
  → Obtén SSID nuevo de PocketOption
  
  "Telegram error"
  → Verifica token y chat ID correctos
  
  "No generates trades"
  → Revisa logs/trades/ para ver qué pasó
  
  "Bot crashes"
  → Ejecuta deploy_check.py para diagnóstico

─────────────────────────────────────────────────────────────────────────

                    ¡LISTO PARA OPERAR! 🚀

─────────────────────────────────────────────────────────────────────────
"""

if __name__ == "__main__":
    print(__doc__)
    
    import os
    if os.path.exists("DEPLOYMENT_GUIDE.md"):
        print("\n💡 Para instrucciones detalladas:")
        print("   cat DEPLOYMENT_GUIDE.md")
        print("\n   O ejecuta:")
        print("   python deploy_check.py")
