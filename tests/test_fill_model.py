# tests/test_fill_model.py
import math
from src.simulator.fill_model import simulate_limit_fill, apply_funding

def make_orderbook_simple():
    # asks: price ascending, bids: price descending
    asks = [
        (100.0, 1.0),  # price, qty
        (100.5, 2.0),
        (101.0, 5.0)
    ]
    bids = [
        (99.5, 1.5),
        (99.0, 3.0),
        (98.5, 10.0)
    ]
    return {"asks": asks, "bids": bids}

def test_full_fill_buy():
    ob = make_orderbook_simple()
    # buy qty that is fully covered by top asks (1.0)
    qty = 1.0
    res = simulate_limit_fill(orderbook=ob, side="buy", qty=qty)
    assert math.isclose(res["filled_qty"], 1.0, rel_tol=1e-9)
    assert res["avg_price"] == 100.0
    assert res["remaining_qty"] == 0.0
    assert res["notional"] == 100.0
    assert len(res["fill_details"]) == 1
    assert res["fill_details"][0][0] == 100.0

def test_partial_fill_buy_insufficient_depth():
    ob = make_orderbook_simple()
    # request more than available in asks (sum asks = 8.0)
    qty = 20.0
    res = simulate_limit_fill(orderbook=ob, side="buy", qty=qty)
    # filled should be sum of asks (1 + 2 + 5 = 8)
    assert math.isclose(res["filled_qty"], 8.0, rel_tol=1e-9)
    assert res["remaining_qty"] == 12.0
    assert res["avg_price"] is not None
    assert res["notional"] > 0

def test_sell_against_bids():
    ob = make_orderbook_simple()
    qty = 2.0
    res = simulate_limit_fill(orderbook=ob, side="sell", qty=qty)
    # sells consume bids: top bid 99.5 qty 1.5, then 99.0 qty 3.0 -> filled 2.0
    assert math.isclose(res["filled_qty"], 2.0, rel_tol=1e-9)
    # avg price should be weighted between 99.5 and 99.0
    assert res["avg_price"] is not None
    assert res["notional"] > 0

def test_slippage_calculation_buy():
    ob = make_orderbook_simple()
    qty = 3.0  # consumes 1.0 @100 and 2.0 @100.5 -> avg = (1*100 + 2*100.5)/3 = 100.333...
    res = simulate_limit_fill(orderbook=ob, side="buy", qty=qty)
    assert math.isclose(res["avg_price"], (1*100.0 + 2*100.5) / 3.0, rel_tol=1e-9)
    assert res["slippage_pct"] is not None

def test_apply_funding_long_short():
    account = {"balance": 1000.0, "positions": {}}
    # create a long position
    account["positions"]["FAKE"] = {"side": "long", "size": 1.0, "entry_price": 100.0}
    payment = apply_funding(account, "FAKE", hours=1.0, funding_rate_per_hour=0.0001)
    # if funding_rate_per_hour > 0, longs pay -> balance decreases
    assert payment >= 0.0
    assert account["balance"] < 1000.0
