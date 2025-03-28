from enum import Enum

class AgentKey:
    # analyst keys
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    INSIDER = "insider"
    NEWS = "news"

    # workflow keys
    PORTFOLIO = "portfolio manager"
    PLANNER = "analyst planner" 

class Signal(str, Enum):
    """Signal type"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"

    def __str__(self) -> str:
        return self.value

class Action(str, Enum):
    """Action type"""
    BUY = "Buy"
    SELL = "Sell"
    HOLD = "Hold"

    def __str__(self) -> str:
        return self.value 