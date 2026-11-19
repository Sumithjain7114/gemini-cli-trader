"""Read-only Angel One SmartAPI market-data access."""

from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from trading_strategy import Candle


INSTRUMENT_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
IST = timezone(timedelta(hours=5, minutes=30))


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Nifty500Scanner/1.0)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except Exception as exc:
        raise RuntimeError(f"Unable to download market reference data from {url}: {exc}") from exc


def load_nifty500_constituents(url: str) -> list[tuple[str, str]]:
    text = _download(url).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    symbol_field = next((name for name in (reader.fieldnames or []) if name.strip().lower() == "symbol"), None)
    if not symbol_field:
        raise ValueError(f"Nifty 500 constituents file at {url} has no Symbol column")
    industry_field = next((name for name in (reader.fieldnames or []) if name.strip().lower() in {"industry", "sector"}), None)
    if not industry_field:
        raise ValueError(f"Nifty 500 constituents file at {url} has no Industry or Sector column")
    constituents = []
    for row in reader:
        symbol = row.get(symbol_field, "").strip()
        industry = row.get(industry_field, "").strip()
        if not symbol and not industry:
            continue
        if not symbol or not industry:
            raise ValueError(f"Nifty 500 constituents file at {url} contains a row without a symbol or industry")
        constituents.append((symbol, industry))
    constituents = sorted(set(constituents))
    if not constituents:
        raise ValueError(f"Nifty 500 constituents file at {url} contains no symbols")
    return constituents


def load_nifty500_symbols(url: str) -> list[str]:
    return [symbol for symbol, _ in load_nifty500_constituents(url)]


class AngelOneMarketData:
    def __init__(self) -> None:
        required = ("ANGELONE_API_KEY", "ANGELONE_CLIENT_CODE", "ANGELONE_PIN", "ANGELONE_TOTP_SECRET")
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise RuntimeError(f"Missing Angel One credentials in environment: {', '.join(missing)}")
        self.api_key = os.environ["ANGELONE_API_KEY"]
        self.client_code = os.environ["ANGELONE_CLIENT_CODE"]
        self.pin = os.environ["ANGELONE_PIN"]
        self.totp_secret = os.environ["ANGELONE_TOTP_SECRET"]
        self.client: Any = None
        self._tokens: dict[tuple[str, str], str] | None = None
        self._last_request = 0.0
        try:
            self._request_delay = float(os.environ.get("ANGELONE_REQUEST_DELAY_SECONDS", "1.0"))
        except ValueError as exc:
            raise ValueError("ANGELONE_REQUEST_DELAY_SECONDS must be numeric") from exc
        if self._request_delay < 0:
            raise ValueError("ANGELONE_REQUEST_DELAY_SECONDS must be non-negative")

    def connect(self) -> None:
        try:
            import pyotp
            from SmartApi import SmartConnect
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt before running the Angel One scanner") from exc
        self.client = SmartConnect(api_key=self.api_key)
        response = self.client.generateSession(
            self.client_code,
            self.pin,
            pyotp.TOTP(self.totp_secret).now(),
        )
        if not isinstance(response, dict) or not response.get("status") or not response.get("data"):
            message = response.get("message", "unknown authentication error") if isinstance(response, dict) else "invalid API response"
            raise RuntimeError(f"Angel One authentication failed: {message}")

    def logout(self) -> None:
        if self.client is not None:
            response = self.client.terminateSession(self.client_code)
            if isinstance(response, dict) and response.get("status") is False:
                raise RuntimeError(f"Angel One logout failed: {response.get('message', 'unknown error')}")

    def _load_tokens(self) -> dict[tuple[str, str], str]:
        if self._tokens is None:
            try:
                records = json.loads(_download(INSTRUMENT_MASTER_URL))
            except json.JSONDecodeError as exc:
                raise RuntimeError("Angel One instrument master is not valid JSON") from exc
            if not isinstance(records, list):
                raise RuntimeError("Angel One instrument master has an unexpected format")
            tokens: dict[tuple[str, str], str] = {}
            for record in records:
                if record.get("exch_seg") != "NSE":
                    continue
                symbol = str(record.get("symbol", "")).upper()
                name = str(record.get("name", "")).upper()
                token = str(record.get("token", ""))
                if token:
                    if symbol:
                        tokens[("symbol", symbol)] = token
                    if name:
                        tokens[("name", name)] = token
            self._tokens = tokens
        return self._tokens

    def _token_for(self, symbol: str) -> str:
        tokens = self._load_tokens()
        normalized = symbol.upper()
        candidates = [
            ("symbol", normalized),
            ("symbol", normalized + "-EQ"),
            ("name", normalized),
        ]
        for key in candidates:
            if key in tokens:
                return tokens[key]
        raise KeyError(f"No NSE instrument token found for {symbol}")

    def candles(self, symbol: str, interval: str, history_days: int) -> list[Candle]:
        if self.client is None:
            raise RuntimeError("Call connect() before requesting market data")
        now = datetime.now(IST)
        start = now - timedelta(days=history_days)
        params = {
            "exchange": "NSE",
            "symboltoken": self._token_for(symbol),
            "interval": interval,
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": now.strftime("%Y-%m-%d %H:%M"),
        }
        wait = self._request_delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        response = self.client.getCandleData(params)
        self._last_request = time.monotonic()
        if not isinstance(response, dict) or not response.get("status"):
            message = response.get("message", "unknown market-data error") if isinstance(response, dict) else "invalid API response"
            raise RuntimeError(f"Angel One candle request failed for {symbol}: {message}")
        data = response.get("data")
        if not isinstance(data, list):
            raise RuntimeError(f"Angel One returned malformed candles for {symbol}")
        candles: list[Candle] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 6:
                raise RuntimeError(f"Angel One returned a malformed candle row for {symbol}")
            candles.append(Candle(
                timestamp=datetime.fromisoformat(str(row[0]).replace("Z", "+00:00")).replace(tzinfo=None),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            ))
        return sorted(candles, key=lambda candle: candle.timestamp)
