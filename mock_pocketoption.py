import asyncio
import random
import uuid

class PocketOptionAsync:
    """Mock implementation of PocketOptionAsync for testing without the real BinaryOptionsToolsV2 library.
    Matches the interface expected by main.py.
    """
    def __init__(self, ssid: str = "mock_ssid"):
        self.ssid = ssid
        self._balance = 1000.0  # Float, as expected by main.py
        self._demo = True
        self.active_trades = {}

    def is_demo(self):
        """Return whether the account is demo."""
        return self._demo

    async def balance(self):
        """Return the current balance as a float."""
        await asyncio.sleep(0.1)  # simulate network delay
        return self._balance

    async def get_candles(self, pair: str, interval: int, lookback: int = 50, offset=0):
        """Return a mock list of candle data (list of dicts or similar, main.py handles conversion).
        main.py expects raw data to be a list of dicts with keys like 'time', 'open', 'close', 'high', 'low'.
        """
        await asyncio.sleep(0.2)  # simulate network delay
        
        # Generate dummy data
        import time
        import random
        
        current_time = int(time.time())
        candles = []
        
        # Start from 'lookback' intervals ago
        start_time = current_time - (lookback * interval)
        
        price = 1.0500 # Base price for EURUSD-ish
        
        for i in range(lookback):
            timestamp = start_time + (i * interval)
            
            # Random walk
            change = (random.random() - 0.5) * 0.0010
            open_price = price
            close_price = price + change
            high_price = max(open_price, close_price) + (random.random() * 0.0005)
            low_price = min(open_price, close_price) - (random.random() * 0.0005)
            
            candles.append({
                "time": timestamp,
                "open": open_price,
                "close": close_price,
                "high": high_price,
                "low": low_price,
                "volume": random.randint(10, 100)
            })
            
            price = close_price

        return candles

    async def buy(self, asset, amount, time, check_win=False):
        """Simulate a buy order."""
        await asyncio.sleep(0.5)
        trade_id = str(uuid.uuid4())[:8]
        self.active_trades[trade_id] = {
            "asset": asset,
            "amount": amount,
            "direction": "call",
            "start_time": asyncio.get_event_loop().time(),
            "duration": time
        }
        # Return trade_id and a dummy result dict
        return trade_id, {"status": "success", "id": trade_id}

    async def sell(self, asset, amount, time, check_win=False):
        """Simulate a sell order."""
        await asyncio.sleep(0.5)
        trade_id = str(uuid.uuid4())[:8]
        self.active_trades[trade_id] = {
            "asset": asset,
            "amount": amount,
            "direction": "put",
            "start_time": asyncio.get_event_loop().time(),
            "duration": time
        }
        return trade_id, {"status": "success", "id": trade_id}

    async def check_win(self, trade_id):
        """Simulate checking the result of a trade."""
        await asyncio.sleep(0.5)
        
        if trade_id not in self.active_trades:
            return {"result": "error", "message": "Trade not found"}
            
        trade = self.active_trades.pop(trade_id)
        amount = trade['amount']
        
        # Random win/loss
        is_win = random.choice([True, False])
        
        if is_win:
            profit = amount * 0.92  # 92% payout
            self._balance += profit
            return {"result": "win", "profit": profit, "win": profit}
        else:
            self._balance -= amount
            return {"result": "loss", "profit": 0, "win": 0}

    async def close(self):
        """Placeholder for closing resources."""
        pass
