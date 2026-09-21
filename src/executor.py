import json
from datetime import datetime
from config import PAPER_TRADE, BINANCE_MARKET_TYPE
from binance_utils import signed_post

LOG_FILE = "logs/trades.jsonl"

def place_trade_paper(account, symbol, side, usd_size, price):
    tx = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "side": side,
        "usd_size": usd_size,
        "price": price,
        "pre_balance": account["balance"],
    }
    account["balance"] -= usd_size
    tx["post_balance"] = account["balance"]
    tx["fees"] = 0.0
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(tx) + "\n")
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
