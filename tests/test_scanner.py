from src.scanner import estimate_probability_from_returns

def test_estimator_range():
    p = estimate_probability_from_returns("BTCUSDT")
    assert 0.0 < p < 1.0
