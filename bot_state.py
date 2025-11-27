"""
Thread-safe state management for trading bot using async locks.
Replaces global variables to prevent race conditions in async execution.
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque


class BotState:
    """Encapsulates all bot state with async-safe access."""
    
    def __init__(self):
        # Locks for each resource
        self._stats_lock = asyncio.Lock()
        self._daily_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        self._streak_lock = asyncio.Lock()
        
        # Trading statistics
        self._stats: Dict[str, int] = {'wins': 0, 'losses': 0, 'total': 0}
        
        # Daily statistics (reset each day)
        self._daily_stats: Dict[str, int] = {
            'trades': 0,
            'losses': 0,
            'last_reset': datetime.now(timezone.utc).date()
        }
        
        # Trade history (rolling window)
        self._trade_history: deque = deque(maxlen=200)
        
        # Streak tracking
        self._streak_losses: int = 0
        
        # Initial balance for drawdown calculation
        self._initial_balance: Optional[float] = None
    
    async def get_stats(self) -> Dict[str, int]:
        """Get current trading statistics."""
        async with self._stats_lock:
            return self._stats.copy()
    
    async def update_stats(self, win: bool):
        """Update statistics after a trade."""
        async with self._stats_lock:
            self._stats['total'] += 1
            if win:
                self._stats['wins'] += 1
            else:
                self._stats['losses'] += 1
    
    async def get_daily_stats(self) -> Dict[str, int]:
        """Get daily statistics, resetting if new day."""
        async with self._daily_lock:
            today = datetime.now(timezone.utc).date()
            if self._daily_stats['last_reset'] != today:
                # New day - reset
                self._daily_stats = {
                    'trades': 0,
                    'losses': 0,
                    'last_reset': today
                }
            return self._daily_stats.copy()
    
    async def increment_daily_trades(self):
        """Increment daily trade counter."""
        async with self._daily_lock:
            today = datetime.now(timezone.utc).date()
            if self._daily_stats['last_reset'] != today:
                self._daily_stats = {
                    'trades': 0,
                    'losses': 0,
                    'last_reset': today
                }
            self._daily_stats['trades'] += 1
    
    async def increment_daily_losses(self):
        """Increment daily loss counter."""
        async with self._daily_lock:
            today = datetime.now(timezone.utc).date()
            if self._daily_stats['last_reset'] != today:
                self._daily_stats = {
                    'trades': 0,
                    'losses': 0,
                    'last_reset': today
                }
            self._daily_stats['losses'] += 1
    
    async def add_trade(self, win: bool, timestamp: Optional[datetime] = None):
        """Add trade to history."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        async with self._history_lock:
            self._trade_history.append({
                'win': win,
                'timestamp': timestamp
            })
    
    async def get_trade_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get trade history (most recent first)."""
        async with self._history_lock:
            history = list(self._trade_history)
            if limit:
                history = history[-limit:]
            return history
    
    async def get_rolling_winrate(self, window: int = 20) -> Optional[float]:
        """Calculate rolling winrate from recent trades."""
        async with self._history_lock:
            if len(self._trade_history) < 10:
                return None
            
            recent = list(self._trade_history)[-window:]
            wins = sum(1 for t in recent if t['win'])
            return wins / len(recent) if recent else None
    
    async def get_streak_losses(self) -> int:
        """Get current losing streak."""
        async with self._streak_lock:
            return self._streak_losses
    
    async def update_streak(self, win: bool):
        """Update losing streak."""
        async with self._streak_lock:
            if win:
                self._streak_losses = 0
            else:
                self._streak_losses += 1
    
    async def reset_streak(self):
        """Reset losing streak to 0."""
        async with self._streak_lock:
            self._streak_losses = 0
    
    async def set_initial_balance(self, balance: float):
        """Set initial balance for drawdown tracking."""
        if self._initial_balance is None:
            self._initial_balance = balance
    
    async def get_initial_balance(self) -> Optional[float]:
        """Get initial balance."""
        return self._initial_balance
    
    async def calculate_drawdown(self, current_balance: float) -> float:
        """Calculate current drawdown percentage."""
        if self._initial_balance is None or self._initial_balance == 0:
            return 0.0
        
        return (self._initial_balance - current_balance) / self._initial_balance
