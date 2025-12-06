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
    
    # Verify daily chart generation
    from datetime import date
    test_date = date(2025, 11, 23) # We know this date has 58 trades
    print(f"\n🔍 Testing daily chart for {test_date}...")
    
    chart_buf, stats = listener._generate_daily_chart(test_date)
    
    if chart_buf and stats:
        print("✅ Chart generated successfully")
        print("📊 Daily Stats:")
        print(f"   Trades: {stats['total_trades']}")
        print(f"   Wins: {stats['wins']}")
        print(f"   Losses: {stats['losses']}")
        print(f"   P&L: {stats['pnl']:.2f}")
    else:
        print("❌ Failed to generate daily chart")

    print("\nListener started. Send /balance, /info, or /info_details to your bot now.")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Stopped")
