# BabyAGI Binance Starter

Minimal BabyAGI-style autonomous agent skeleton adapted to Binance.

**Features**
- 10-minute agent loop scanning top symbols
- Deterministic placeholder probability estimator
- Kelly sizing with 6% cap and fractional Kelly option
- Paper-trade default with optional live execution (Binance testnet/live)
- JSONL logging for scans, decisions, and trades
- Dockerized for reproducible runs

**Quick start**
1. Copy `.env.example` to `.env` and set values.
2. (Paper-trade) Ensure `PAPER_TRADE=true`.
3. Build and run:
   - `docker compose up --build`
4. Inspect logs in `logs/`.

**Important**
- Do not commit real API keys.
- Test thoroughly on Binance testnet before any live trading.
