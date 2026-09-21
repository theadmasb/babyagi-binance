def kelly_fraction(p_win, odds):
    """
    Binary Kelly for bet with decimal odds b (payout per unit risk).
    p_win: estimated probability of winning (0-1)
    odds: decimal odds received on a win (e.g., if market price q=0.3, odds = (1-q)/q)
    """
    b = odds
    if b <= 0:
        return 0.0
    f_star = (b * p_win - (1 - p_win)) / b
    return f_star

def capped_kelly(p_win, market_price, max_fraction, fractional=1.0):
    """
    market_price: interpreted as probability-like price q (0-1) for mapping to odds.
    Returns a non-negative fraction capped at max_fraction.
    """
    q = market_price
    if q <= 0 or q >= 1:
        return 0.0
    odds = (1 - q) / q
    f = kelly_fraction(p_win, odds)
    f = f * fractional
    if f <= 0:
        return 0.0
    return min(f, max_fraction)
