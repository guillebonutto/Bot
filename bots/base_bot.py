"""
Base Bot - Shared functionality for all specialized bots
"""
import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict
from dotenv import load_dotenv

# Import existing components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
except ImportError:
    from mock_pocketoption import PocketOptionAsync

from risk_manager import RiskManager
from bot_state import BotState
from logger_config import setup_logger
from config_loader import load_config
from bots.ml_filter import MLFilter


class BaseBot:
    """
    Base class for all specialized trading bots.
    Handles common functionality: API connection, risk management, logging, ML filtering.
    """
    
    def __init__(self, bot_name: str, env_file: str = None):
        """
        Args:
            bot_name: Name of the bot (e.g., 'ema_pullback')
            env_file: Optional .env file to load (defaults to .env)
        """
        self.bot_name = bot_name
        
        # Load environment
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Setup logger
        self.logger = setup_logger(
            name=f"bot_{bot_name}",
            log_file=f"logs/bot_{bot_name}.log",
            level=logging.INFO
        )
        
        # Load config
        self.config = load_config()
        
        # Get credentials
        self.ssid = os.getenv("POCKETOPTION_SSID")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.ssid:
            raise ValueError("POCKETOPTION_SSID not found in environment")
            
        if not self.ssid:
            raise ValueError("POCKETOPTION_SSID not found in environment")
            
        # NOTE: We do NOT clean the SSID because the library seems to expect the raw format 
        # or at least doesn't crash with it (returns -1 instead of ValueError).
        # We will handle the connection failure downstream.
        
        # Initialize API with robust error handling
        try:
            self.api = PocketOptionAsync(ssid=self.ssid)
        except Exception as e:
            self.log(f"❌ Error initializing Real API: {e}", "error")
            self.log("⚠️ Falling back to SIMULATION MODE (Mock API) due to initialization failure.", "warning")
            from mock_pocketoption import PocketOptionAsync as MockApi
            self.api = MockApi()
        except Exception as e:
            self.log(f"❌ Error initializing Real API: {e}", "error")
            self.log("⚠️ Falling back to SIMULATION MODE (Mock API) due to initialization failure.", "warning")
            from mock_pocketoption import PocketOptionAsync as MockApi
            self.api = MockApi()
            
        # Check which library is being used
        lib_name = self.api.__class__.__module__
        self.log(f"📚 API Library: {lib_name}")
        
        # Initialize state management
        self.bot_state = BotState()
        
        # Initialize risk manager
        risk_config = self.config['risk']
        system_config = self.config['system']
        self.risk_manager = RiskManager(
            max_daily_losses=risk_config['max_daily_losses'],
            max_daily_trades=risk_config['max_daily_trades'],
            risk_per_trade=risk_config['risk_per_trade'],
            max_drawdown=risk_config['max_drawdown'],
            streak_limit=risk_config['streak_limit'],
            max_risk_per_trade=risk_config.get('max_risk_per_trade', 0.05),
            demo_mode=system_config.get('demo_mode', True)
        )
        
        # Initialize ML filter
        model_path = f"models/{bot_name}_model.pkl"
        ml_threshold = float(os.getenv("ML_THRESHOLD", "0.65"))
        self.ml_filter = MLFilter(model_path, threshold=ml_threshold)
        
        # Bot-specific config
        self.timeframes = os.getenv("TIMEFRAMES", "M5").split(",")
        self.pairs = self.config['trading']['pairs']
        self.sleep_interval = int(os.getenv("SLEEP_INTERVAL", "30"))
        
        self.log(f"🤖 {bot_name.upper()} Bot initialized")
        self.log(f"📊 Timeframes: {self.timeframes}")
        self.log(f"💰 ML Threshold: {ml_threshold}")
    
    def log(self, msg: str, level: str = "info"):
        """Log message with bot name prefix."""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(f"[{self.bot_name}] {msg}")
    
    async def generate_signal(self) -> Optional[Dict]:
        """
        Generate trading signal based on bot's strategy.
        Must be implemented by each specialized bot.
        
        Returns:
            Dict with signal details or None
        """
        raise NotImplementedError("Each bot must implement generate_signal()")
    
    async def execute_trade(self, signal: Dict):
        """
        Execute a trade based on signal.
        
        Args:
            signal: Signal dict with pair, direction, etc.
        """
        try:
            # Get current balance
            balance = await self.api.balance()
            
            # Check risk limits
            can_trade, reason = await self.risk_manager.can_trade(balance, self.bot_state)
            if not can_trade:
                self.log(f"🛡️ Trade blocked: {reason}", "warning")
                return
            
            # Calculate position size
            amount = self.risk_manager.calculate_position_size(balance)
            
            # Log trade
            self.log(
                f"🚀 EXECUTING: {signal['pair']} {signal['direction']} "
                f"${amount:.2f} (Score: {signal.get('score', 'N/A')})"
            )
            
            # Send Telegram notification
            self.send_telegram(
                f"🚀 SEÑAL EJECUTADA\n"
                f"Bot: {self.bot_name}\n"
                f"Par: {signal['pair']}\n"
                f"Dirección: {signal['direction']}\n"
                f"Score: {signal.get('score', 'N/A')}\n"
                f"Patrón: {signal.get('pattern', 'N/A')}\n"
                f"Precio: {signal.get('price', 'N/A')}\n"
                f"Monto: ${amount:.2f}"
            )
            
            # TODO: Execute actual trade via API
            # result = await self.api.open_trade(...)
            
            # For now, simulate
            self.log(f"✅ Trade simulado (remove this in production)", "debug")
            
            # Record trade
            await self.bot_state.add_trade({
                'pair': signal['pair'],
                'direction': signal['direction'],
                'amount': amount,
                'timestamp': datetime.now(timezone.utc),
                'bot': self.bot_name
            })
            
        except Exception as e:
            self.log(f"❌ Error executing trade: {e}", "error")
    
    def send_telegram(self, message: str):
        """Send Telegram notification."""
        if not self.telegram_token or not self.telegram_chat_id:
            self.log(f"[Telegram not configured] {message}", "debug")
            return
        
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={"chat_id": self.telegram_chat_id, "text": message},
                timeout=10
            )
            self.log("📱 Telegram notification sent", "debug")
        except Exception as e:
            self.log(f"⚠️ Error sending Telegram: {e}", "warning")
    
    async def run(self):
        """
        Main bot loop.
        """
        self.log("=" * 70)
        self.log(f"🚀 {self.bot_name.upper()} BOT STARTING")
        self.log("=" * 70)
        
        # Get initial balance with retry logic (like main.py)
        balance = None
        for attempt in range(3):
            try:
                balance = await self.api.balance()
                
                # If valid balance found, break
                if balance != -1 and balance != -1.0:
                    break
                
                # If invalid, wait and retry
                if attempt < 2:
                    self.log(f"⚠️ Balance check failed ({balance}), retrying ({attempt + 1}/3)...", "warning")
                    await asyncio.sleep(2)
            except Exception as e:
                self.log(f"⚠️ Error getting balance ({attempt + 1}/3): {e}", "warning")
                await asyncio.sleep(2)
        
        # Final check
        if balance is None or balance == -1 or balance == -1.0:
            self.log("❌ Connection rejected by server after 3 attempts.", "error")
            self.log("👉 This usually means your SSID is expired or invalid.", "warning")
            self.log("⚠️ Switching to SIMULATION MODE to keep bot running.", "warning")
            
            from mock_pocketoption import PocketOptionAsync as MockApi
            self.api = MockApi()
            balance = await self.api.balance()
            self.log("✅ Switched to Mock API", "info")
            
        is_demo = self.api.is_demo()
        self.log(f"✅ Account: {'DEMO' if is_demo else 'REAL'} - Balance: ${balance:.2f}")
        
        cycle = 0
        
        while True:
            try:
                cycle += 1
                
                # Generate signal
                signal = await self.generate_signal()
                
                if signal:
                    # Extract features for ML filter
                    features = signal.get('features', {})
                    
                    # Check ML filter
                    ml_proba = self.ml_filter.predict(features)
                    
                    if ml_proba >= self.ml_filter.threshold:
                        self.log(
                            f"✅ Signal passed ML filter: {signal['pair']} "
                            f"(ML: {ml_proba:.2%})"
                        )
                        await self.execute_trade(signal)
                    else:
                        self.log(
                            f"⏸️ Signal rejected by ML: {signal['pair']} "
                            f"(ML: {ml_proba:.2%} < {self.ml_filter.threshold:.2%})",
                            "debug"
                        )
                
                # Sleep
                await asyncio.sleep(self.sleep_interval)
                
            except KeyboardInterrupt:
                self.log("🛑 Bot stopped by user")
                break
            except Exception as e:
                self.log(f"⚠️ Error in main loop: {e}", "error")
                await asyncio.sleep(60)


if __name__ == "__main__":
    # This is just a base class, run specific bots instead
    print("❌ BaseBot is an abstract class. Run a specific bot instead:")
    print("   python bots/bot_ema_pullback.py")
    print("   python bots/bot_trend_following.py")
    print("   python bots/bot_round_levels.py")
