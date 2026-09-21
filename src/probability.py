# src/probability.py
import math
import logging
from typing import List, Tuple

from binance_utils import public_get

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MIN_PROB = 0.001
MAX_PROB = 0.999

def _log_returns_from_klines(klines: List[List]) -> List[float]:
    """
    Convert Binance minute klines to log returns.
    klines: list of kline arrays as returned by /api/v3/klines:
      [ openTime, open, high, low, close, volume, closeTime, ... ]
    Returns list of log(close_t / close_{t-1})
    """
    closes = [float(k[4]) for k in klines]
    if len(closes) < 2:
        return []
    returns = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if prev <= 0 or cur <= 0:
            # skip invalid data points
            continue
        returns.append(math.log(cur / prev))
    return returns

def _normal_cdf(z: float) -> float:
    """Standard normal CDF using math.erf for portability."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def compute_market_implied_probability(
    symbol: str,
    price: float,
    horizon_minutes: int,
    lookback_minutes: int = 120,
    market_type: str = "FUTURES"
) -> float:
    """
    Estimate probability that price_{t+H} > price_t using historical minute returns.
    - symbol: Binance symbol, e.g., "BTCUSDT"
    - price: current price (float)
    - horizon_minutes: H (integer)
    - lookback_minutes: number of past minutes to use for estimating mu and sigma
    - market_type: "FUTURES" or "SPOT" (passed to public_get)
    Returns p in (0,1), clipped to [0.001, 0.999].
    """
    try:
        # Binance klines endpoint: interval=1m, limit=lookback_minutes+1 to get lookback returns
        futures = (market_type.upper() == "FUTURES")
        path = "/fapi/v1/klines" if futures else "/api/v3/klines"
        params = {"symbol": symbol, "interval": "1m", "limit": lookback_minutes + 1}
        klines = public_get(path, params=params, futures=futures)
    except Exception as e:
        logger.warning("Failed to fetch klines for %s: %s", symbol, e)
        # fallback: return neutral probability
        return 0.5

    returns = _log_returns_from_klines(klines)
    if not returns:
        return 0.5

    # estimate per-minute drift (mu) and volatility (sigma)
    n = len(returns)
    mean_r = sum(returns) / n
    # sample variance
    var = sum((r - mean_r) ** 2 for r in returns) / max(1, n - 1)
    sigma = math.sqrt(var) if var > 0 else 0.0
    mu = mean_r  # per-minute drift estimate

    H = max(1, int(horizon_minutes))
    # If sigma is extremely small, use a deterministic sign from mu
    if sigma < 1e-12:
        p = 0.999 if mu > 0 else 0.001 if mu < 0 else 0.5
        return max(MIN_PROB, min(MAX_PROB, p))

    # z = (ln(threshold/price) - mu*H) / (sigma * sqrt(H))
    # For threshold = price (probability price increases), ln(threshold/price) = 0
    z = (-mu * H) / (sigma * math.sqrt(H))
    p = 1.0 - _normal_cdf(z)
    # clip to avoid extremes
    return max(MIN_PROB, min(MAX_PROB, p))
