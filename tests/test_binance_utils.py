# tests/test_binance_utils.py
import os
import time
import hmac
import hashlib
from urllib.parse import urlencode

import pytest

import src.binance_utils as bu

def test_generate_signature_matches_hmac():
    secret = "testsecret123"
    params = {"symbol": "BTCUSDT", "timestamp": 1600000000000}
    # expected computed directly
    query = urlencode(params, doseq=True)
    expected = hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    got = bu.generate_signature(params, secret=secret)
    assert got == expected

def test_build_signed_query_includes_timestamp_and_signature():
    secret = "anothersecret"
    params = {"symbol": "ETHUSDT"}
    q = bu._build_signed_query(params, secret=secret)
    # parse back to ensure timestamp and signature present
    assert "timestamp=" in q
    assert "signature=" in q
