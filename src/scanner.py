import random
import numpy as np
from binance_utils import public_get
from config import BINANCE_TOP_SYMBOLS_LIMIT, BINANCE_HORIZON_MINUTES, BINANCE_MARKET_TYPE
from probability import compute_market_implied_probability

def compute_market_implied_probability(symbol, price, horizon_minutes):
    # fetch recent minute returns (or use historical sample)
    # estimate mean and std of log returns, assume normal for short horizon
    # compute probability price_t+H > price_now
    mu = 0.0  # estimated drift per minute
    sigma = 0.001  # placeholder; compute from data
    H = horizon_minutes
    # probability price increases = 1 - CDF( (ln(1) - mu*H) / (sigma*sqrt(H)) )
    from math import log, sqrt
    z = (0 - mu * H) / (sigma * sqrt(H))
    from scipy.stats import norm
    p = 1 - norm.cdf(z)
    return max(0.001, min(0.999, p))

def list_top_symbols(limit=BINANCE_TOP_SYMBOLS_LIMIT, market_type=BINANCE_MARKET_TYPE):
    futures = (market_type.upper() == "FUTURES")
    path = "/fapi/v1/ticker/24hr" if futures else "/api/v3/ticker/24hr"
    tickers = public_get(path, futures=futures)
    tickers_sorted = sorted(tickers, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
    symbols = []
    for t in tickers_sorted[:limit]:
        symbols.append({
            "symbol": t["symbol"],
            "price": float(t.get("lastPrice", t.get("lastPrice", 0))),
            "quoteVolume": float(t.get("quoteVolume", 0))
        })
    return symbols

def get_orderbook(symbol, limit=5, market_type=BINANCE_MARKET_TYPE):
    futures = (market_type.upper() == "FUTURES")
    path = "/fapi/v1/depth" if futures else "/api/v3/depth"
    params = {"symbol": symbol, "limit": limit}
    ob = public_get(path, params=params, futures=futures)
    bids = [(float(p), float(q)) for p, q in ob.get("bids", [])]
    asks = [(float(p), float(q)) for p, q in ob.get("asks", [])]
    return {"bids": bids, "asks": asks}

def compute_model_probability(symbol, price, horizon_minutes, market_type="FUTURES"):
    """
    Agent's model probability (p_est). Use a longer lookback to smooth noise.
    """
    # longer lookback for model (e.g., 240 minutes)
    lookback = 240
    return compute_market_implied_probability(
        symbol=symbol,
        price=price,
        horizon_minutes=horizon_minutes,
        lookback_minutes=lookback,
        market_type=market_type
    )

def compute_market_probability_short(symbol, price, horizon_minutes, market_type="FUTURES"):
    """
    Market-implied probability (q). Use a short lookback so it reflects recent market pricing.
    """
    # short lookback for market-implied (e.g., 20 minutes)
    lookback = 20
    return compute_market_implied_probability(
        symbol=symbol,
        price=price,
        horizon_minutes=horizon_minutes,
        lookback_minutes=lookback,
        market_type=market_type
    )

def scan_universe(limit=BINANCE_TOP_SYMBOLS_LIMIT, market_type=BINANCE_MARKET_TYPE):
    symbols = list_top_symbols(limit=limit, market_type=market_type)
    snapshot = []
    for s in symbols:
        ob = get_orderbook(s["symbol"], limit=5, market_type=market_type)
        # compute both probabilities
        p_est = compute_model_probability(s["symbol"], s["price"], horizon_minutes=BINANCE_HORIZON_MINUTES, market_type=market_type)
        q_market = compute_market_probability_short(s["symbol"], s["price"], horizon_minutes=BINANCE_HORIZON_MINUTES, market_type=market_type)
        snapshot.append({
            "symbol": s["symbol"],
            "price": s["price"],
            "quoteVolume": s["quoteVolume"],
            "orderbook": ob,
            "p_est": p_est,
            "q_market": q_market
        })
    return snapshot
