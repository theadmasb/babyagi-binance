# src/binance_utils.py
import os
import time
import hmac
import hashlib
import logging
from urllib.parse import urlencode
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_USE_TESTNET

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SPOT_BASE = "https://testnet.binance.vision" if BINANCE_USE_TESTNET else "https://api.binance.com"
FUTURES_BASE = "https://testnet.binancefuture.com" if BINANCE_USE_TESTNET else "https://fapi.binance.com"

# Session with retries and backoff
_session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
)
_adapter = HTTPAdapter(max_retries=retries)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

DEFAULT_TIMEOUT = 10  # seconds

def _timestamp():
    return int(time.time() * 1000)

def generate_signature(params: dict, secret: str = None) -> str:
    """
    Generate HMAC-SHA256 signature for Binance API.
    Returns hex digest string.
    """
    if secret is None:
        secret = BINANCE_API_SECRET
    # Ensure deterministic ordering
    query_string = urlencode(params, doseq=True)
    signature = hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature

def _build_signed_query(params: dict, secret: str = None) -> str:
    """
    Add timestamp and signature to params and return query string.
    """
    if params is None:
        params = {}
    params = dict(params)  # copy
    params.setdefault("timestamp", _timestamp())
    signature = generate_signature(params, secret=secret)
    params["signature"] = signature
    return urlencode(params, doseq=True)

def _request_with_retry(method: str, url: str, **kwargs):
    """
    Wrapper around session.request with logging and error handling.
    """
    try:
        resp = _session.request(method, url, timeout=kwargs.pop("timeout", DEFAULT_TIMEOUT), **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        logger.warning("HTTP error %s for %s %s: %s", resp.status_code if 'resp' in locals() else None, method, url, e)
        raise
    except requests.exceptions.RequestException as e:
        logger.warning("Request exception for %s %s: %s", method, url, e)
        raise

def public_get(path: str, params: dict = None, futures: bool = False):
    base = FUTURES_BASE if futures else SPOT_BASE
    url = base + path
    return _request_with_retry("GET", url, params=params)

def signed_get(path: str, params: dict = None, futures: bool = False, api_key: str = None, api_secret: str = None):
    """
    Signed GET: signature appended to query string. Uses X-MBX-APIKEY header.
    """
    base = FUTURES_BASE if futures else SPOT_BASE
    query = _build_signed_query(params or {}, secret=api_secret)
    url = f"{base}{path}?{query}"
    headers = {"X-MBX-APIKEY": api_key or BINANCE_API_KEY}
    return _request_with_retry("GET", url, headers=headers)

def signed_post(path: str, params: dict = None, futures: bool = False, api_key: str = None, api_secret: str = None):
    """
    Signed POST: signature appended to query string (Binance expects signature in query string for many endpoints).
    """
    base = FUTURES_BASE if futures else SPOT_BASE
    query = _build_signed_query(params or {}, secret=api_secret)
    url = f"{base}{path}?{query}"
    headers = {"X-MBX-APIKEY": api_key or BINANCE_API_KEY}
    return _request_with_retry("POST", url, headers=headers)
