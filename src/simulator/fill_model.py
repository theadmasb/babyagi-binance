# src/simulator/fill_model.py
"""
Book-level fill simulation for paper trading.

Functions:
- simulate_limit_fill(orderbook, side, qty, price_limit=None, fee_rate=0.0006)
- apply_funding(account, symbol, hours, funding_rate_per_hour)
"""

from typing import Dict, List, Tuple, Optional

# orderbook format expected:
# {"bids": [(price1, qty1), (price2, qty2), ...],
#  "asks": [(price1, qty1), (price2, qty2), ...]}
# bids sorted desc by price, asks sorted asc by price

DEFAULT_TAKER_FEE = 0.0006  # 0.06% typical taker fee (adjust to your account)
DEFAULT_MAKER_FEE = 0.0002  # 0.02% typical maker fee (adjust as needed)


def _consume_levels(levels: List[Tuple[float, float]], qty: float) -> Tuple[float, float, List[Tuple[float, float]]]:
    """
    Consume quantity from book levels.

    Returns:
      filled_qty, weighted_price_numerator, remaining_levels
    weighted_price_numerator is sum(price * filled_at_that_level_qty)
    """
    remaining = []
    filled = 0.0
    weighted = 0.0
    qty_left = qty

    for price, level_qty in levels:
        if qty_left <= 0:
            remaining.append((price, level_qty))
            continue
        take = min(level_qty, qty_left)
        filled += take
        weighted += take * price
        qty_left -= take
        # if level has leftover, append remaining
        if level_qty - take > 0:
            remaining.append((price, level_qty - take))

    # append any untouched deeper levels (if we iterated through all and qty_left <=0, remaining already has them)
    return filled, weighted, remaining


def simulate_limit_fill(
    orderbook: Dict[str, List[Tuple[float, float]]],
    side: str,
    qty: float,
    price_limit: Optional[float] = None,
    fee_rate: float = DEFAULT_TAKER_FEE
) -> Dict:
    """
    Simulate filling a limit order against the provided top-of-book snapshot.

    Parameters
    - orderbook: dict with 'bids' and 'asks' lists of (price, qty)
    - side: "buy" or "sell" (from the perspective of the agent)
    - qty: desired base-asset quantity to buy/sell
    - price_limit: optional limit price; if provided, do not fill beyond that price
    - fee_rate: fraction charged on notional (use taker fee for immediate fills)

    Returns a dict:
    {
      "requested_qty": qty,
      "filled_qty": filled_qty,
      "avg_price": avg_price (None if filled_qty==0),
      "notional": notional (sum price*filled_qty),
      "fees": fees (in quote currency),
      "slippage_pct": (avg_price - reference_price)/reference_price,
      "remaining_qty": qty - filled_qty,
      "fill_details": [(price, qty_filled_at_price), ...]
    }
    Notes:
    - For buys, we consume asks (lowest first).
    - For sells, we consume bids (highest first).
    - price_limit is inclusive: buy limit means only fill asks <= price_limit; sell limit means only fill bids >= price_limit.
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")

    asks = orderbook.get("asks", []) or []
    bids = orderbook.get("bids", []) or []

    # reference price for slippage calculation: top-of-book mid or top price depending on side
    ref_price = None
    if side == "buy":
        ref_price = asks[0][0] if asks else None
    else:
        ref_price = bids[0][0] if bids else None

    # choose levels to consume
    if side == "buy":
        levels = asks  # ascending prices
    else:
        levels = bids  # descending prices

    # apply price_limit filter to levels
    filtered_levels = []
    for price, level_qty in levels:
        if price_limit is not None:
            if side == "buy" and price > price_limit:
                break
            if side == "sell" and price < price_limit:
                break
        filtered_levels.append((price, level_qty))

    filled_qty, weighted, remaining = _consume_levels(filtered_levels, qty)

    avg_price = None
    notional = 0.0
    fees = 0.0
    fill_details = []

    if filled_qty > 0:
        avg_price = weighted / filled_qty
        notional = weighted  # quote currency amount
        fees = notional * fee_rate
        # reconstruct fill_details by comparing filtered_levels and remaining
        qty_left = filled_qty
        for price, level_qty in filtered_levels:
            take = min(level_qty, qty_left)
            if take > 0:
                fill_details.append((price, take))
                qty_left -= take
            if qty_left <= 0:
                break

    slippage_pct = None
    if avg_price is not None and ref_price is not None and ref_price > 0:
        # for buy: slippage = (avg_price - ref_price) / ref_price
        # for sell: slippage = (ref_price - avg_price) / ref_price (positive if worse)
        if side == "buy":
            slippage_pct = (avg_price - ref_price) / ref_price
        else:
            slippage_pct = (ref_price - avg_price) / ref_price

    return {
        "requested_qty": qty,
        "filled_qty": filled_qty,
        "avg_price": avg_price,
        "notional": notional,
        "fees": fees,
        "slippage_pct": slippage_pct,
        "remaining_qty": max(0.0, qty - filled_qty),
        "fill_details": fill_details,
        "ref_price": ref_price
    }


def apply_funding(account: Dict, symbol: str, hours: float, funding_rate_per_hour: float):
    """
    Apply funding payments to the account for an open position on symbol.

    - account: dict with 'positions' mapping symbol -> position dict
      position dict expected keys: 'side' ('long'/'short'), 'size' (base qty), 'entry_price'
    - hours: number of hours to apply funding for (can be fractional)
    - funding_rate_per_hour: signed funding rate per hour (positive means longs pay shorts)

    This function deducts/adds funding in quote currency from account['balance'] and records in account['funding_history'].
    """
    if "positions" not in account or symbol not in account["positions"]:
        return 0.0

    pos = account["positions"][symbol]
    size = pos.get("size", 0.0)
    entry_price = pos.get("entry_price", pos.get("avg_price", None))
    if size == 0 or entry_price is None:
        return 0.0

    # notional exposure in quote currency
    notional = abs(size) * entry_price
    funding_payment = notional * funding_rate_per_hour * hours

    # determine payer/receiver: if funding_rate_per_hour > 0, longs pay shorts
    # pos['side'] expected 'long' or 'short'
    side = pos.get("side", "long")
    if funding_rate_per_hour > 0:
        if side == "long":
            account["balance"] -= funding_payment
        else:
            account["balance"] += funding_payment
    else:
        # negative funding: shorts pay longs
        if side == "short":
            account["balance"] -= funding_payment
        else:
            account["balance"] += funding_payment

    # record
    account.setdefault("funding_history", []).append({
        "symbol": symbol,
        "hours": hours,
        "funding_rate_per_hour": funding_rate_per_hour,
        "payment": funding_payment
    })
    return funding_payment
