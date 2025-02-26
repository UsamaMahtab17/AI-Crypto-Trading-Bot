from typing import Optional, Dict, Any
from pydantic import BaseModel

# Request schema
class StrategyParams(BaseModel):
    short_window: Optional[int] = None  # Required for MACD
    long_window: Optional[int] = None  # Required for MACD
    signal_window: Optional[int] = None  # Required for MACD
    period: Optional[int] = None  # Required for RSI
    short_period: Optional[int] = None  # Required for EMA
    long_period: Optional[int] = None  # Required for EMA
    window: Optional[int] = None  # Required for Bollinger Bands
    multiplier: Optional[float] = None  # Required for Bollinger Bands

class StartBotRequest(BaseModel):
    pair: str
    strategy_id: str
    strategy: str  # e.g., "MACD", "RSI", "EMA", "Bollinger Bands"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    params: Optional[StrategyParams] = None