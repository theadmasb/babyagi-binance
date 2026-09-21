import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_USE_TESTNET

SPOT_BASE = "https://testnet.binance.vision" if BINANCE_USE_TESTNET else "https://api.binance.com"
FUTURES_BASE = "https://testnet.binancefuture.com" if BINANCE_USE_TESTNET else "https://fapi.binance.com"

def _timestamp():
    return int(time.time() * 1000)

def _sign(params):
    query_string = urlencode(params)
    signature = hmac.new(BINANCE_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{query_string}&signature={signature}"

def public_get(path, params=None, futures=False):
    base = FUTURES_BASE if futures else SPOT_BASE
    url = base + path
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def signed_get(path, params=None, futures=False):
    if params is None:
        params = {}
    params['timestamp'] = _timestamp()
    signed = _sign(params)
    base = FUTURES_BASE if futures else SPOT_BASE
    url = base + path + "?" + signed
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def signed_post(path, params=None, futures=False):
    if params is None:
        params = {}
    params['timestamp'] = _timestamp()
    signed = _sign(params)
    base = FUTURES_BASE if futures else SPOT_BASE
    url = base + path + "?" + signed
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    r = requests.post(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()
