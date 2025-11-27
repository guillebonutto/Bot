"""
Signal type definitions and enums for trading bot.
Provides type safety and clarity for signal generation.
"""
from enum import Enum


class Direction(Enum):
    """Trading direction."""
    BUY = "BUY"
    SELL = "SELL"
    
    def __str__(self):
        return self.value


class SignalSource(Enum):
    """Source of trading signal."""
    INDICATOR = "indicator"
    PATTERN = "pattern"
    COMBINED = "combined"  # Indicator + Pattern confirmation
    
    def __str__(self):
        return self.value


class PatternType(Enum):
    """Types of chart patterns."""
    DOUBLE_TOP = "doble_techo"
    COMPRESSION = "compresion"
    FLAG = "flag"
    TRIANGLE = "triangulo"
    CHANNEL_BREAKOUT = "ruptura_canal"
    RSI_DIVERGENCE = "divergencia_rsi"
    MACD_DIVERGENCE = "divergencia_macd"
    
    def __str__(self):
        return self.value
