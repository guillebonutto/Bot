"""
Risk management module with strict validation and circuit breakers.
Prevents catastrophic losses through enforced limits and drawdown protection.
"""
from typing import Tuple, Optional
from bot_state import BotState


class RiskManager:
    """Enforces risk limits and protects against catastrophic losses."""
    
    def __init__(
        self,
        max_daily_losses: int = 3,
        max_daily_trades: int = 10,
        risk_per_trade: float = 0.02,
        max_drawdown: float = 0.10,
        streak_limit: int = 2,
        max_risk_per_trade: float = 0.05
    ):
        """
        Initialize risk manager with strict limits.
        
        Args:
            max_daily_losses: Maximum losses allowed per day
            max_daily_trades: Maximum trades allowed per day
            risk_per_trade: Percentage of balance to risk per trade (0.01-0.05)
            max_drawdown: Maximum drawdown before circuit breaker (0.05-0.20)
            streak_limit: Pause after N consecutive losses
            max_risk_per_trade: Absolute maximum risk per trade
        """
        # Validate parameters
        if not 0.01 <= risk_per_trade <= 0.05:
            raise ValueError(f"risk_per_trade must be between 0.01 and 0.05, got {risk_per_trade}")
        
        if not 0.05 <= max_drawdown <= 1.0:
            raise ValueError(f"max_drawdown must be between 0.05 and 1.0, got {max_drawdown}")
        
        if max_daily_losses < 1:
            raise ValueError(f"max_daily_losses must be >= 1, got {max_daily_losses}")
        
        self.max_daily_losses = max_daily_losses
        self.max_daily_trades = max_daily_trades
        self.risk_per_trade = risk_per_trade
        self.max_drawdown = max_drawdown
        self.streak_limit = streak_limit
        self.max_risk_per_trade = max_risk_per_trade
        
        self._circuit_breaker_active = False
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5
    
    async def can_trade(
        self,
        balance: float,
        bot_state: BotState
    ) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on all risk criteria.
        
        Args:
            balance: Current account balance
            bot_state: Bot state instance
        
        Returns:
            (can_trade, reason/amount)
            - If can_trade is True, reason contains the trade amount
            - If can_trade is False, reason contains the blocking reason
        """
        # 1. Check circuit breaker
        if self._circuit_breaker_active:
            return False, "🚨 Circuit breaker activo - bot pausado por errores críticos"
        
        # 2. Check minimum balance
        if balance < 1.0:
            return False, f"💰 Balance insuficiente: ${balance:.2f} < $1.00"
        
        # 3. Check daily loss limit
        daily_stats = await bot_state.get_daily_stats()
        if daily_stats['losses'] >= self.max_daily_losses:
            return False, f"🛑 Límite de pérdidas diarias alcanzado ({self.max_daily_losses})"
        
        # 4. Check daily trade limit
        if daily_stats['trades'] >= self.max_daily_trades:
            return False, f"📊 Límite de trades diarios alcanzado ({self.max_daily_trades})"
        
        # 5. Check losing streak
        streak = await bot_state.get_streak_losses()
        if streak >= self.streak_limit:
            return False, f"⚠️ Racha de {streak} pérdidas - pausa de seguridad"
        
        # 6. Check drawdown
        initial_balance = await bot_state.get_initial_balance()
        if initial_balance is not None:
            drawdown = await bot_state.calculate_drawdown(balance)
            if drawdown >= self.max_drawdown:
                self._circuit_breaker_active = True
                return False, f"🚨 STOP-LOSS GLOBAL: Drawdown {drawdown*100:.1f}% >= {self.max_drawdown*100:.1f}%"
        
        # 7. Calculate trade amount
        amount = balance * self.risk_per_trade
        
        # Cap at max risk
        max_amount = balance * self.max_risk_per_trade
        amount = min(amount, max_amount)
        
        # Ensure minimum $1
        amount = max(amount, 1.0)
        
        # Final check: don't risk more than balance
        if amount > balance:
            return False, f"⚠️ Amount calculado (${amount:.2f}) > balance (${balance:.2f})"
        
        return True, f"${amount:.2f}"
    
    def record_error(self):
        """Record a consecutive error. Activates circuit breaker if threshold reached."""
        self._consecutive_errors += 1
        if self._consecutive_errors >= self._max_consecutive_errors:
            self._circuit_breaker_active = True
    
    def reset_errors(self):
        """Reset error counter after successful operation."""
        self._consecutive_errors = 0
    
    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is active."""
        return self._circuit_breaker_active
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker (use with caution)."""
        self._circuit_breaker_active = False
        self._consecutive_errors = 0
    
    def get_status(self) -> dict:
        """Get current risk manager status."""
        return {
            'circuit_breaker': self._circuit_breaker_active,
            'consecutive_errors': self._consecutive_errors,
            'limits': {
                'max_daily_losses': self.max_daily_losses,
                'max_daily_trades': self.max_daily_trades,
                'risk_per_trade': f"{self.risk_per_trade*100:.1f}%",
                'max_drawdown': f"{self.max_drawdown*100:.1f}%",
                'streak_limit': self.streak_limit
            }
        }
