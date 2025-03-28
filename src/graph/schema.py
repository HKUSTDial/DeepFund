import operator
from typing import  List, Dict, Any, Optional
from typing_extensions import TypedDict, Annotated
from pydantic import BaseModel, Field
from graph.constants import Signal, Action


class AnalystSignal(BaseModel):
    """Signal from analyst"""
    signal: str = Field(
        description="Choose from Bullish, Bearish, or Neutral",
        default=str(Signal.NEUTRAL)
    )
    justification: str = Field(
        description="Brief explanation for the signal",
        default="No justification provided due to error"
    )

class Decision(BaseModel):
    """Decision made by portfolio manager"""
    action: str = Field( 
        description="Choose from Buy, Sell, or Hold",
        default=str(Action.HOLD)
    )
    shares: int = Field(
        description="Number of shares to buy or sell, set 0 for hold",
        default=0
    )
    price: Optional[float] = Field(
        description="Trading price for the ticker.",
        default=None
    )
    justification: str = Field(
        description="Brief explanation for the decision",
        default="Just hold due to error"
    )

class Position(BaseModel):
    value: float = Field(
        default=0.0,
        description="Monetary value for the position."
    )
    shares: int = Field(
        default=0,
        description="Shares for the position."
    )

class Portfolio(BaseModel):
    """Portfolio state when running the workflow."""
    cashflow: float = Field(description="Cashflow for the fund.")
    positions: dict[str, Position] = Field(description="Positions for each ticker.")

class FundState(TypedDict):
    """Fund state when running the workflow."""

    # from environment
    ticker: str = Field(description="Ticker in-the-flow.")
    portfolio: Portfolio = Field(description="Portfolio for the fund.")
    llm_config: Dict[str, Any] = Field(description="LLM configuration.")
    
    # updated by workflow
    # ticker -> signal of all analysts
    analyst_signals: Annotated[List[AnalystSignal], operator.add]
    # portfolio manager output
    decision: Decision
    