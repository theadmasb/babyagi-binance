# src/executor.py
import json
from datetime import datetime
from config import PAPER_TRADE, BINANCE_MARKET_TYPE
from binance_utils import signed_post
from simulator.fill_model import simulate_limit_fill

LOG_FILE = "logs/trades.jsonl"
POSITIONS_FILE = "logs/positions.jsonl"

def _write_jsonl(path, obj):
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")

def place_trade_paper(account, symbol, side, usd_size, price):
    """
    Paper trade that simulates fills against top-of-book snapshot.
    - account: dict with 'balance' and optional 'positions' mapping
    - symbol: trading symbol
    - side: 'buy' or 'sell'
    - usd_size: notional in quote currency to spend (for buys) or receive (for sells)
    - price: reference price (top-of-book)
    """
    # convert USD notional to base quantity using reference price
    if price is None or price <= 0:
        raise ValueError("Invalid price for conversion")

    qty = usd_size / price

    # attempt to use last known orderbook snapshot if available in account metadata
    # caller should pass orderbook snapshot in decision logs; here we expect account to have 'last_orderbooks'
    orderbook = None
    if "last_orderbooks" in account and symbol in account["last_orderbooks"]:
        orderbook = account["last_orderbooks"][symbol]
    else:
        # fallback: no depth -> zero fill
        orderbook = {"bids": [], "asks": []}

    # simulate fill
    fill = simulate_limit_fill(orderbook=orderbook, side=side, qty=qty, price_limit=None, fee_rate=None)

    # compute fees: if simulate_limit_fill returned fees None (because fee_rate None), compute using default
    fees = fill.get("fees", 0.0)

    # update account balance and positions
    # For buys: account pays notional + fees; for sells: account receives notional - fees
    if side.lower() == "buy":
        # deduct notional + fees
        account["balance"] -= (fill["notional"] + fees)
        # add/update position
        pos = account.setdefault("positions", {}).get(symbol)
        if pos:
            # average into existing long
            existing_size = pos.get("size", 0.0)
            existing_avg = pos.get("avg_price", 0.0)
            new_size = existing_size + fill["filled_qty"]
            if new_size > 0:
                new_avg = ((existing_avg * existing_size) + (fill["avg_price"] * fill["filled_qty"])) / new_size
            else:
                new_avg = fill["avg_price"]
            account["positions"][symbol] = {
                "side": "long",
                "size": new_size,
                "avg_price": new_avg,
                "last_updated": datetime.utcnow().isoformat()
            }
        else:
            account.setdefault("positions", {})[symbol] = {
                "side": "long",
                "size": fill["filled_qty"],
                "avg_price": fill["avg_price"],
                "last_updated": datetime.utcnow().isoformat()
            }
    else:
        # sell: reduce or create short
        account["balance"] += (fill["notional"] - fees)
        pos = account.setdefault("positions", {}).get(symbol)
        if pos and pos.get("side") == "long":
            # reduce long position
            existing_size = pos.get("size", 0.0)
            remaining = max(0.0, existing_size - fill["filled_qty"])
            if remaining == 0:
                # position closed
                account["positions"].pop(symbol, None)
            else:
                account["positions"][symbol] = {
                    "side": "long",
                    "size": remaining,
                    "avg_price": pos.get("avg_price"),
                    "last_updated": datetime.utcnow().isoformat()
                }
        else:
            # open/increase short
            existing = account.setdefault("positions", {}).get(symbol)
            if existing and existing.get("side") == "short":
                new_size = existing.get("size", 0.0) + fill["filled_qty"]
                # average price for shorts: weighted average of entry prices
                existing_avg = existing.get("avg_price", 0.0)
                new_avg = ((existing_avg * existing.get("size", 0.0)) + (fill["avg_price"] * fill["filled_qty"])) / new_size
                account["positions"][symbol] = {
                    "side": "short",
                    "size": new_size,
                    "avg_price": new_avg,
                    "last_updated": datetime.utcnow().isoformat()
                }
            else:
                account["positions"][symbol] = {
                    "side": "short",
                    "size": fill["filled_qty"],
                    "avg_price": fill["avg_price"],
                    "last_updated": datetime.utcnow().isoformat()
                }

    # record trade log
    tx = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "side": side,
        "requested_usd": usd_size,
        "requested_qty": qty,
        "filled_qty": fill["filled_qty"],
        "avg_price": fill["avg_price"],
        "notional": fill["notional"],
        "fees": fees,
        "slippage_pct": fill["slippage_pct"],
        "pre_balance": None,  # caller may populate if desired
        "post_balance": account["balance"],
        "position": account.get("positions", {}).get(symbol)
    }
    _write_jsonl(LOG_FILE, tx)
    _write_jsonl(POSITIONS_FILE, {"timestamp": datetime.utcnow().isoformat(), "positions": account.get("positions", {})})
    return tx


def _usd_to_quantity(symbol, usd_amount, price, market_type=BINANCE_MARKET_TYPE):
    qty = usd_amount / price
    return float("{:.8f}".format(qty))

def place_trade_live(account, symbol, side, usd_size, price, market_type=BINANCE_MARKET_TYPE):
    if PAPER_TRADE:
        return place_trade_paper(account, symbol, side, usd_size, price)

    futures = (market_type.upper() == "FUTURES")
    qty = _usd_to_quantity(symbol, usd_size, price, market_type=market_type)
    if futures:
        path = "/fapi/v1/order"
        params = {
            "symbol": symbol,
            "side": "BUY" if side.lower() == "buy" else "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": qty,
            "price": str(price),
            "recvWindow": 5000
        }
    else:
        path = "/api/v3/order"
        params = {
            "symbol": symbol,
            "side": "BUY" if side.lower() == "buy" else "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": qty,
            "price": str(price),
            "recvWindow": 5000
        }
    resp = signed_post(path, params=params, futures=futures)
    tx = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "side": side,
        "usd_size": usd_size,
        "price": price,
        "response": resp
    }
    account["balance"] -= usd_size
    tx["post_balance"] = account["balance"]
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(tx) + "\n")
    return tx
