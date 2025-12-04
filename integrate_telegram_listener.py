"""
Script para integrar telegram_listener en bot_ema_pullback.py
"""

import re

def integrate_listener():
    bot_file = "bots/bot_ema_pullback.py"
    
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Agregar import
    if "from telegram_listener import TelegramListener" not in content:
        import_section = "from telegram_formatter import telegram, send_trade_signal, send_trade_result"
        new_import = import_section + "\nfrom telegram_listener import TelegramListener"
        content = content.replace(import_section, new_import)
    
    # 2. Inicializar listener antes del loop principal
    # Buscamos un buen lugar, por ejemplo después de inicializar el modelo ML
    
    listener_init = r'''
# ========================= TELEGRAM LISTENER =========================
# Iniciar listener para comandos /balance y /info
def get_current_balance():
    return api.balance

telegram_listener = TelegramListener(TELEGRAM_TOKEN, get_current_balance)
telegram_listener.start()
'''
    
    # Insertar antes de "print('Iniciando análisis...')"
    if "telegram_listener =" not in content:
        target = 'print("Iniciando análisis...")'
        content = content.replace(target, listener_init + '\n    ' + target)
    
    with open(bot_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Telegram Listener integrado en bot_ema_pullback.py")

if __name__ == "__main__":
    integrate_listener()
