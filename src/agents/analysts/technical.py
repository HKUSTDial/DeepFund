import math
import pandas as pd

from graph.schema import FundState, AnalystSignal
from graph.constants import Signal, AgentKey
from graph.prompt import TECHNICAL_PROMPT
from llm.inference import agent_call
from apis.hub import get_price_data
from util.logger import logger

# Technical Thresholds
thresholds = {
    "trend": {
        "short": 8,
        "medium": 21,
        "long": 55,
    },
    "mean_reversion": {
        "bollinger_window": 20,
        "rolling_window": 50,
        "z_score_extreme": 2.0,
        "bb_position_threshold": 0.2
    },
    "rsi": {
        "period": 14,
        "bullish": 30,
        "bearish": 70,
    },
    "momentum": {
        "bullish": 0.05,
        "bearish": -0.05,
    },
    "volatility": {
        "bullish": 0.8,
        "bearish": 1.2,
    }
}


def technical_agent(state: FundState):
    """Technical analysis specialist that excels at short to medium-term price movement predictions."""
    agent_name = AgentKey.TECHNICAL
    start_date = state["start_date"]
    end_date = state["end_date"]
    ticker = state["ticker"]
    llm_config = state["llm_config"]

    logger.log_agent_status(agent_name, ticker, "Analyzing price data")

    # Get the price data
    prices_df = get_price_data(ticker=ticker, start_date=start_date, end_date=end_date)
    if prices_df is None:
        logger.error(f"Failed to fetch price data for {ticker}")
        return state
    
    # Analyze technical indicators
    signal_results = {
        "trend": get_trend_signal(prices_df, thresholds["trend"]),
        "mean_reversion": get_mean_reversion_signal(prices_df, thresholds["mean_reversion"]),
        "rsi": get_rsi_signal(prices_df, thresholds["rsi"]),
        "momentum": get_momentum_signal(prices_df, thresholds["momentum"]),
        "volatility":  get_volatility_signal(prices_df, thresholds["volatility"]),
    }

    # Make prompt
    prompt = TECHNICAL_PROMPT.format(
        ticker=ticker,
        analysis=signal_results
    )

    # Get LLM signal
    signal = agent_call(
        prompt=prompt,
        llm_config=llm_config,
        pydantic_model=AnalystSignal
    )

    logger.log_signal(agent_name, ticker, signal)

    return {"analyst_signals": [signal]}


def get_trend_signal(prices_df, params):
    """Advanced trend following strategy using multiple timeframes and indicators"""

    def _calculate_ema(prices_df, window):
        return prices_df["close"].ewm(span=window, adjust=False).mean()

    # Calculate EMAs for multiple timeframes
    ema_short = _calculate_ema(prices_df, params["short"])
    ema_medium = _calculate_ema(prices_df, params["medium"])
    ema_long = _calculate_ema(prices_df, params["long"])

    # Determine trend direction and strength
    short_trend = ema_short > ema_medium
    medium_trend = ema_medium > ema_long

    if short_trend.iloc[-1] and medium_trend.iloc[-1]:
        signal = Signal.BULLISH
    elif not short_trend.iloc[-1] and not medium_trend.iloc[-1]:
        signal = Signal.BEARISH
    else:
        signal = Signal.NEUTRAL

    return signal


def get_mean_reversion_signal(prices_df, params):
    """Mean reversion strategy using statistical measures and Bollinger Bands"""
    
    def _calculate_bollinger_bands(prices_df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
        sma = prices_df["close"].rolling(window).mean()
        std_dev = prices_df["close"].rolling(window).std()
        upper_band = sma + (std_dev * 2)
        lower_band = sma - (std_dev * 2)
        return upper_band, lower_band

    # Calculate Bollinger Bands with configured window
    bb_upper, bb_lower = _calculate_bollinger_bands(prices_df, params["bollinger_window"])

    # Calculate z-score with configured rolling window
    ma = prices_df["close"].rolling(window=params["rolling_window"]).mean()
    std = prices_df["close"].rolling(window=params["rolling_window"]).std()
    z_score = (prices_df["close"] - ma) / std

    # Calculate normalized position within Bollinger Bands
    price_vs_bb = (prices_df["close"].iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])

    # Use threshold values for signal conditions
    if z_score.iloc[-1] < params["z_score_extreme"] and price_vs_bb < params["bb_position_threshold"]:
        signal = Signal.BULLISH
    elif z_score.iloc[-1] > params["z_score_extreme"] and price_vs_bb > (1 - params["bb_position_threshold"]):
        signal = Signal.BEARISH
    else:
        signal = Signal.NEUTRAL

    return signal


def get_rsi_signal(prices_df, params):
    """RSI signal that indicate overbought/oversold conditions"""

    def _calculate_rsi(prices_df: pd.DataFrame, period: int) -> pd.Series:
        delta = prices_df["close"].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    rsi = _calculate_rsi(prices_df, params["period"])
    if rsi.iloc[-1] > params["bearish"]:
        signal = Signal.BEARISH
    elif rsi.iloc[-1] < params["bullish"]:
        signal = Signal.BULLISH
    else:
        signal = Signal.NEUTRAL

    return signal


def get_momentum_signal(prices_df, params):
    """Multi-factor momentum strategy"""

    # Price momentum with fixed months
    returns = prices_df["close"].pct_change()
    mom_1m = returns.rolling(21).sum()
    mom_3m = returns.rolling(63).sum()
    mom_6m = returns.rolling(126).sum()

    # Calculate momentum score
    momentum_score = (0.4 * mom_1m + 0.3 * mom_3m + 0.3 * mom_6m).iloc[-1]

    # Volume momentum and confirmation
    volume_ma = prices_df["volume"].rolling(21).mean()
    volume_momentum = prices_df["volume"] / volume_ma
    volume_confirmation = volume_momentum.iloc[-1] > 1.0

    if momentum_score > params["bullish"] and volume_confirmation:
        signal = Signal.BULLISH
    elif momentum_score < params["bearish"] and volume_confirmation:
        signal = Signal.BEARISH
    else:
        signal = Signal.NEUTRAL

    return signal


def get_volatility_signal(prices_df, params):
    """Volatility-based trading strategy"""
    # Calculate various volatility metrics
    returns = prices_df["close"].pct_change()

    # Historical volatility
    hist_vol = returns.rolling(21).std() * math.sqrt(252)

    # Volatility regime detection
    vol_ma = hist_vol.rolling(63).mean()
    vol_regime = hist_vol / vol_ma

    # Volatility mean reversion
    vol_z_score = (hist_vol - vol_ma) / hist_vol.rolling(63).std()

    # Generate signal based on volatility regime
    current_vol_regime = vol_regime.iloc[-1]
    vol_z = vol_z_score.iloc[-1]

    if current_vol_regime < params["bullish"] and vol_z < -1:
        # Low vol regime, potential for expansion
        signal = Signal.BULLISH
    elif current_vol_regime > params["bearish"] and vol_z > 1:
        # High vol regime, potential for contraction
        signal = Signal.BEARISH
    else:
        signal = Signal.NEUTRAL

    return signal