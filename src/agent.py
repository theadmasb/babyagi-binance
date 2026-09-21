import time
from config import *
from scanner import scan_universe
from kelly import capped_kelly
from executor import place_trade_paper, place_trade_live

def run_once(account):
    snapshot = scan_universe(limit=SCAN_LIMIT, market_type=BINANCE_MARKET_TYPE)
    for m in snapshot:
        p_est = m["p_est"]
        market_price = m["price"]
        # Note: market_price is not a probability; this placeholder uses the same threshold logic
        if abs(p_est - market_price) >= MISPRICING_THRESHOLD:
            bet_fraction = capped_kelly(p_est, market_price, MAX_BET_FRACTION, FRACTIONAL_KELLY)
            if bet_fraction <= 0:
                continue
            bet_size = account["balance"] * bet_fraction
            top_ask_qty = m["orderbook"]["asks"][0][1] if m["orderbook"]["asks"] else 0
            top_bid_qty = m["orderbook"]["bids"][0][1] if m["orderbook"]["bids"] else 0
            if bet_size > max(top_ask_qty, top_bid_qty) * market_price * 0.5:
                continue
            side = "buy" if p_est > market_price else "sell"
            if PAPER_TRADE:
                place_trade_paper(account, m["symbol"], side, bet_size, market_price)
            else:
                place_trade_live(account, m["symbol"], side, bet_size, market_price)

def run_scheduler(account):
    import schedule
    schedule.every(SCAN_INTERVAL_MIN).minutes.do(run_once, account=account)
    while True:
        schedule.run_pending()
        time.sleep(1)
