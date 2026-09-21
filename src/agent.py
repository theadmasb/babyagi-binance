import time
from config import *
from scanner import scan_universe
from kelly import capped_kelly
from executor import place_trade_paper, place_trade_live
from logger import log_scan, log_decision

def run_once(account):
    snapshot = scan_universe(limit=SCAN_LIMIT, market_type=BINANCE_MARKET_TYPE)
    # log the scan snapshot (optional)
    log_scan(snapshot)
    for m in snapshot:
        p_est = m.get("p_est")
        q_market = m.get("q_market")
        # sanity checks
        if p_est is None or q_market is None:
            continue
        # mispricing check: compare probabilities, not raw price
        if abs(p_est - q_market) < MISPRICING_THRESHOLD:
            continue

        # compute Kelly fraction using market-implied probability q_market as the "market price"
        bet_fraction = capped_kelly(p_win=p_est, market_price=q_market, max_fraction=MAX_BET_FRACTION, fractional=FRACTIONAL_KELLY)
        if bet_fraction <= 0:
            continue

        bet_size = account["balance"] * bet_fraction

        # liquidity filter: require top depth to be able to absorb the notional
        top_ask_qty = m["orderbook"]["asks"][0][1] if m["orderbook"]["asks"] else 0
        top_bid_qty = m["orderbook"]["bids"][0][1] if m["orderbook"]["bids"] else 0
        # approximate top depth in USD
        top_depth_usd = max(top_ask_qty, top_bid_qty) * m["price"]
        if bet_size > top_depth_usd * 0.5:
            # skip if our bet would consume too much top-of-book depth
            continue

        # decide side: buy if model expects price to go up relative to market
        side = "buy" if p_est > q_market else "sell"

        decision = {
            "timestamp": time.time(),
            "symbol": m["symbol"],
            "p_est": p_est,
            "q_market": q_market,
            "mispricing": p_est - q_market,
            "bet_fraction": bet_fraction,
            "bet_size": bet_size,
            "side": side
        }
        log_decision(decision)

        if PAPER_TRADE:
            place_trade_paper(account, m["symbol"], side, bet_size, m["price"])
        else:
            place_trade_live(account, m["symbol"], side, bet_size, m["price"])

def run_scheduler(account):
    import schedule
    schedule.every(SCAN_INTERVAL_MIN).minutes.do(run_once, account=account)
    while True:
        schedule.run_pending()
        time.sleep(1)
