# tests/test_agent_mispricing.py
import json
import os
from types import SimpleNamespace

import pytest

import src.agent as agent
import src.scanner as scanner
from src.executor import place_trade_paper

def fake_scan_universe_one():
    # create a single symbol snapshot where p_est and q_market differ by 0.2
    return [{
        "symbol": "FAKESYM",
        "price": 100.0,
        "quoteVolume": 1000.0,
        "orderbook": {"bids": [(99.5, 1.0)], "asks": [(100.5, 1.0)]},
        "p_est": 0.7,
        "q_market": 0.5
    }]

def test_agent_places_paper_trade_on_mispricing(monkeypatch, tmp_path):
    # monkeypatch scan_universe to return our fake snapshot
    monkeypatch.setattr("src.agent.scan_universe", lambda limit, market_type: fake_scan_universe_one())
    # ensure logs dir
    os.makedirs("logs", exist_ok=True)
    # start with $100
    account = {"balance": 100.0}
    # run one cycle
    agent.run_once(account)
    # check that balance decreased (paper trade placed)
    assert account["balance"] < 100.0
