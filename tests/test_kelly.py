from src.kelly import kelly_fraction, capped_kelly

def test_kelly_basic():
    f = kelly_fraction(0.6, 1.0)
    assert isinstance(f, float)

def test_capped_kelly():
    f = capped_kelly(0.6, 0.5, 0.06, fractional=0.5)
    assert 0.0 <= f <= 0.06
