#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_telegram_formatter.py
===========================
Prueba de los mensajes formateados para Telegram
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from telegram_formatter import TelegramFormatter
from datetime import datetime

# Crear formateador (sin enviar si no está configurado)
formatter = TelegramFormatter()

print("=" * 80)
print("🧪 PRUEBA DE MENSAJES FORMATEADOS PARA TELEGRAM")
print("=" * 80)

# 1. Señal de Trading
print("\n📈 1. MENSAJE DE SEÑAL DE TRADING:")
print("-" * 80)
message1 = """
<b>🎯 NUEVA SEÑAL</b>

<b>Par:</b> 🇪🇺/🇺🇸 EURUSD_otc
<b>Dirección:</b> 📈 BUY
<b>Timeframe:</b> ⏱️ M5
<b>Precio:</b> 💲 1.09500

<i>⏰ """ + datetime.now().strftime('%H:%M:%S') + """</i>
"""
print(message1)

# 2. Resultado WIN
print("\n✅ 2. MENSAJE DE RESULTADO - WIN:")
print("-" * 80)
message2 = """
<b>🏁 OPERACIÓN FINALIZADA</b>

<b>Resultado:</b> ✅ WIN
<b>Par:</b> 🇪🇺/🇺🇸 EURUSD_otc
<b>Dirección:</b> 📈 BUY
<b>Monto:</b> 💵 $10.00
<b>Ganancia/Pérdida:</b> 📈 $+5.50

<i>⏰ """ + datetime.now().strftime('%H:%M:%S') + """</i>
"""
print(message2)

# 3. Resultado LOSS
print("\n❌ 3. MENSAJE DE RESULTADO - LOSS:")
print("-" * 80)
message3 = """
<b>🏁 OPERACIÓN FINALIZADA</b>

<b>Resultado:</b> ❌ LOSS
<b>Par:</b> 🇬🇧/🇺🇸 GBPUSD_otc
<b>Dirección:</b> 📉 SELL
<b>Monto:</b> 💵 $10.00
<b>Ganancia/Pérdida:</b> 📉 $-3.50

<i>⏰ """ + datetime.now().strftime('%H:%M:%S') + """</i>
"""
print(message3)

# 4. Sesión iniciada
print("\n🚀 4. MENSAJE DE SESIÓN INICIADA:")
print("-" * 80)
message4 = """
<b>🚀 SESIÓN INICIADA</b>

<b>Bot:</b> Bot EMA Pullback
<b>Hora:</b> ⏰ """ + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + """

Estado: ✅ Operando
        
"""
print(message4)

# 5. Estadísticas diarias
print("\n📊 5. MENSAJE DE ESTADÍSTICAS DIARIAS:")
print("-" * 80)
message5 = """
<b>📊 RESUMEN DIARIO</b>

<b>Operaciones:</b> 📈 15
<b>Ganancias:</b> ✅ 10
<b>Pérdidas:</b> ❌ 5
<b>Tasa de Ganancia:</b> 📊 66.7%
<b>Balance:</b> 💰 $250.50

<i>⏰ """ + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + """</i>
"""
print(message5)

# 6. Error
print("\n⚠️ 6. MENSAJE DE ERROR:")
print("-" * 80)
message6 = """
<b>❌ ERROR (Bot EMA)</b>

<b>Mensaje:</b>
<code>Connection timeout: Unable to reach API server</code>

<i>⏰ """ + datetime.now().strftime('%H:%M:%S') + """</i>
        
"""
print(message6)

# 7. Alerta de balance bajo
print("\n⚠️ 7. MENSAJE DE ALERTA DE BALANCE BAJO:")
print("-" * 80)
message7 = """
<b>⚠️ ALERTA DE BALANCE</b>

<b>Balance Actual:</b> 💰 $35.50
<b>Umbral Crítico:</b> 🔴 $50.00

⚠️ El balance es bajo. Considera hacer depósito.

<i>⏰ """ + datetime.now().strftime('%H:%M:%S') + """</i>
        
"""
print(message7)

# 8. Estado del sistema
print("\n🔔 8. MENSAJE DE ESTADO DEL SISTEMA:")
print("-" * 80)
message8 = """
<b>🔔 ESTADO DEL SISTEMA</b>

<b>Pares Monitoreados:</b> 📊 4
<b>Bots Activos:</b> 🤖 2
<b>Balance:</b> 💰 $500.00

Estado: ✅ En operación

<i>⏰ """ + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + """</i>
        
"""
print(message8)

print("\n" + "=" * 80)
print("✅ VISTA PREVIA DE MENSAJES COMPLETADA")
print("=" * 80)

print("""
📌 CÓMO USAR EN TU CÓDIGO:

from telegram_formatter import send_trade_signal, send_trade_result

# Enviar señal de trading
send_trade_signal(
    pair="EURUSD_otc",
    direction="BUY",
    price=1.0950,
    timeframe="M5",
    confidence=85.5
)

# Enviar resultado de operación
send_trade_result(
    pair="EURUSD_otc",
    direction="BUY",
    amount=10.0,
    result="WIN",
    profit_loss=5.50
)

# Enviar estadísticas diarias
send_daily_stats(
    total_trades=15,
    wins=10,
    losses=5,
    winrate=66.7,
    balance=250.50
)

# Enviar error
send_error(
    error_msg="Connection timeout: Unable to reach API server",
    bot_name="Bot EMA"
)

# Más métodos disponibles en telegram_formatter.py


💡 CONFIGURACIÓN REQUERIDA EN .env:

TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here


🔗 OBTENER TELEGRAM BOT TOKEN:

1. Ve a https://t.me/BotFather
2. Escribe: /newbot
3. Sigue las instrucciones
4. Copia el token y pégalo en .env


📍 OBTENER CHAT ID:

1. Inicia tu bot en Telegram
2. Envía cualquier mensaje
3. Ve a: https://api.telegram.org/bot<TOKEN>/getUpdates
4. Reemplaza <TOKEN> con tu token real
5. Busca "chat": {"id": 123456789}
6. Ese número es tu CHAT_ID
7. Pégalo en .env
""")
