"""
Test script for Telegram Listener
"""
import os
import time
from dotenv import load_dotenv
from telegram_listener import TelegramListener

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

def get_balance():
    return 1234.56

if __name__ == "__main__":
    if not TOKEN:
        print("❌ No token found")
        exit()
        
    print(f"Testing with token: {TOKEN[:5]}...")
    
    listener = TelegramListener(TOKEN, get_balance)
    listener.start()
    
    print("Listener started. Send /balance or /info to your bot now.")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Stopped")
