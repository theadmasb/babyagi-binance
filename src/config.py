import os
from dotenv import load_dotenv
load_dotenv()

SCAN_LIMIT = int(os.getenv("SCAN_LIMIT", "2000"))
SCAN_INTERVAL_MIN = int(os.getenv("SCAN_INTERVAL_MIN", "10"))
MISPRICING_THRESHOLD = float(os.getenv("MISPRICING_THRESHOLD", "0.08"))
MAX_BET_FRACTION = float(os.getenv("MAX_BET_FRACTION", "0.06"))
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "50.0"))
PAPER_TRADE = os.getenv("PAPER_TRADE", "true").lower() == "true"
FRACTIONAL_KELLY = float(os.getenv("FRACTIONAL_KELLY", "0.5"))

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_USE_TESTNET = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"
BINANCE_MARKET_TYPE = os.getenv("BINANCE_MARKET_TYPE", "FUTURES")
BINANCE_TOP_SYMBOLS_LIMIT = int(os.getenv("BINANCE_TOP_SYMBOLS_LIMIT", "2000"))
BINANCE_HORIZON_MINUTES = int(os.getenv("BINANCE_HORIZON_MINUTES", "60"))
