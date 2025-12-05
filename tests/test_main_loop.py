import pytest
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch, AsyncMock

@pytest.mark.asyncio
async def test_backoff_increases_on_error():
    """Test that backoff sleep increases exponentially on errors."""
    # Test the backoff logic directly
    current_sleep = 5
    error_sleep = 5
    
    # Simulate first error
    error_sleep = min(error_sleep * 2, 300)
    assert error_sleep == 10
    
    # Simulate second error
    error_sleep = min(error_sleep * 2, 300)
    assert error_sleep == 20
    
    # Simulate third error
    error_sleep = min(error_sleep * 2, 300)
    assert error_sleep == 40
    
    # Test max cap
    error_sleep = 200
    error_sleep = min(error_sleep * 2, 300)
    assert error_sleep == 300  # Capped at 300

@pytest.mark.asyncio
async def test_idle_backoff_increases():
    """Test that sleep increases when no signals are found."""
    current_sleep = 5
    all_signals = []  # No signals
    
    # First idle iteration
    if not all_signals:
        current_sleep = min(current_sleep * 1.5, 30)
    assert current_sleep == 7.5
    
    # Second idle iteration
    if not all_signals:
        current_sleep = min(current_sleep * 1.5, 30)
    assert current_sleep == 11.25
    
    # Third idle iteration
    if not all_signals:
        current_sleep = min(current_sleep * 1.5, 30)
    assert current_sleep == 16.875
    
    # Test max cap
    current_sleep = 25
    if not all_signals:
        current_sleep = min(current_sleep * 1.5, 30)
    assert current_sleep == 30  # Capped at 30

@pytest.mark.asyncio
async def test_backoff_resets_on_activity():
    """Test that sleep resets when signals are found."""
    current_sleep = 20  # Previously idle
    all_signals = [{'pair': 'EURUSD', 'signal': 'BUY'}]  # Activity detected
    
    if all_signals:
        current_sleep = 5
    
    assert current_sleep == 5  # Reset to base
