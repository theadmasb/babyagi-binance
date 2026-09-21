# tests/test_probability.py
import math
from urllib.parse import urlencode

import pytest

import src.probability as prob

# A small helper to create synthetic klines: [openTime, open, high, low, close, volume, closeTime, ...]
def make_klines_from_prices(prices):
    klines = []
    t = 1600000000000
    for p in prices:
        klines.append([t, str(p), str(p), str(p), str(p), "0", t + 60000, "0", 0, 0, 0, 0])
        t += 60000
    return klines

def test_log_returns_from_klines():
    prices = [100.0, 101.0, 102.0]
    klines = make_klines_from_prices(prices)
    returns = prob._log_returns_from_klines(klines)
    assert len(returns) == 2
    # check first return approx ln(101/100)
    assert math.isclose(returns[0], math.log(101.0 / 100.0), rel_tol=1e-9)

def test_compute_probability_increasing_series(monkeypatch):
    # synthetic increasing prices -> positive mu -> p > 0.5
    prices = [100 + i * 0.1 for i in range(121)]  # 121 points -> 120 returns
    klines = make_klines_from_prices(prices)

    def fake_public_get(path, params=None, futures=False):
        return klines

    monkeypatch.setattr("src.probability.public_get", fake_public_get)
    p = prob.compute_market_implied_probability("FAKESYM", price=prices[-1], horizon_minutes=60, lookback_minutes=120)
    assert 0.5 < p <= 0.999

def test_compute_probability_flat_series(monkeypatch):
    # flat prices -> mu ~ 0, sigma ~ 0 -> p ~ 0.5
    prices = [100.0] * 121
    klines = make_klines_from_prices(prices)

    def fake_public_get(path, params=None, futures=False):
        return klines

    monkeypatch.setattr("src.probability.public_get", fake_public_get)
    p = prob.compute_market_implied_probability("FAKESYM", price=100.0, horizon_minutes=60, lookback_minutes=120)
    assert 0.499 <= p <= 0.501

def test_compute_probability_decreasing_series(monkeypatch):
    # decreasing prices -> negative mu -> p < 0.5
    prices = [100 - i * 0.1 for i in range(121)]
    klines = make_klines_from_prices(prices)

    def fake_public_get(path, params=None, futures=False):
        return klines

    monkeypatch.setattr("src.probability.public_get", fake_public_get)
    p = prob.compute_market_implied_probability("FAKESYM", price=prices[-1], horizon_minutes=60, lookback_minutes=120)
    assert 0.001 <= p < 0.5
