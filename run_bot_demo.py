"""
run_bot_demo.py
===============
Inicia el bot en DEMO mode sin pedir input (testing).
"""

import os
import sys
import asyncio

# Configurar variables de entorno
os.environ["TELEGRAM_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""

# Importar y ejecutar
from main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Detenido")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
