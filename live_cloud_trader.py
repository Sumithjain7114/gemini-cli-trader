"""Scheduled Nifty 500 signal scanner. No order placement is implemented."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from angelone_data import AngelOneMarketData, load_nifty500_constituents
from trading_strategy import (
    Candle,
    PaperPosition,
    evaluate_paper_position,
    load_config,
    load_paper_state,
    recent_win_rate,
    relative_strength_percentiles,
    save_paper_state,
    scan_symbol,
    simple_moving_average,
)


TABLE_PATH = Path(__file__).with_name("risk_reward_expectancy.csv")
IST = timezone(timedelta(hours=5, minutes=30))


def _validate_universe_config(constituents: list[tuple[str, str]], config: dict[str, Any]) -> dict[str, str]:
    industry_map = {industry.strip().casefold(): index for industry, index in config["sector_index_by_industry"].items()}
    missing = sorted({industry for _, industry in constituents if industry.strip().casefold() not in industry_map})
    if missing:
        preview = ", ".join(missing[:10])
        suffix = "..." if len(missing) > 10 else ""
        raise ValueError(f"Configure a sector index for every Nifty 500 industry; missing: {preview}{suffix}")
    unconfigured = sorted(set(industry_map.values()) - set(config["sector_index_symbols"]))
    if unconfigured:
        raise ValueError(f"sector_index_symbols is missing configured indices: {', '.join(unconfigured)}")
    return {
        symbol: industry_map[industry.strip().casefold()]
        for symbol, industry in constituents
    }


def _below_average(candles: list[Candle], period: int) -> bool:
    if len(candles) < period:
        raise ValueError(f"Index history needs at least {period} candles for its 200-DMA regime filter")
    average = simple_moving_average([c.close for c in candles], period)[-1]
    return average is None or candles[-1].close < average


def _exit_reference(position: PaperPosition, candle: Candle, reason: str) -> float:
    if reason in {"support_stop", "trailing_stop"}:
        level = position.trailing_stop if reason == "trailing_stop" else position.initial_stop
        return min(candle.open, level) if candle.open < level else level
    return candle.close


def _evaluate_position_history(
    position: PaperPosition,
    candles: list[Candle],
    config: dict[str, Any],
    current_time: datetime,
) -> tuple[str | None, Candle]:
    latest = candles[-1]
    previous_timestamp = (
        datetime.fromisoformat(position.last_evaluated_timestamp)
        if position.last_evaluated_timestamp
        else None
    )
    entry_timestamp = datetime.fromisoformat(position.entry_time)
    if entry_timestamp.date() < candles[0].timestamp.date():
        raise ValueError(
            f"History for {position.symbol} starts after its entry date; increase signal_history_days"
        )
    new_candles = [
        candle for candle in candles
        if previous_timestamp is None or candle.timestamp > previous_timestamp
    ]
    for candle in new_candles:
        reason = evaluate_paper_position(position, candle, config)
        position.last_evaluated_timestamp = candle.timestamp.isoformat()
        if reason:
            return reason, candle
    reason = evaluate_paper_position(position, latest, config, current_time=current_time)
    position.last_evaluated_timestamp = latest.timestamp.isoformat()
    return reason, latest


def run_scan(config: dict[str, Any], market: AngelOneMarketData) -> dict[str, Any]:
    constituents = load_nifty500_constituents(config["nifty500_csv_url"])
    symbols = [symbol for symbol, _ in constituents]
    sector_by_symbol = _validate_universe_config(constituents, config)
    needed_symbols = set(symbols)
    needed_symbols.add(config["market_index_symbol"])
    needed_symbols.update(config["sector_index_symbols"])
    state = load_paper_state(config["paper_state_path"])
    win_rate = recent_win_rate(state, config["rolling_win_rate_trades"])

    market.connect()
    try:
        daily_histories = {
            symbol: market.candles(symbol, "ONE_DAY", config["daily_history_days"])
            for symbol in sorted(needed_symbols)
        }
        signal_histories = (
            daily_histories
            if config["candle_interval"] == "ONE_DAY"
            else {
                symbol: market.candles(symbol, config["candle_interval"], config["signal_history_days"])
                for symbol in symbols
            }
        )
    finally:
        market.logout()

    market_bearish = _below_average(
        daily_histories[config["market_index_symbol"]],
        config["market_200dma_period"],
    )
    sector_eligibility = {
        index_symbol: not _below_average(daily_histories[index_symbol], config["sector_index_period"])
        for index_symbol in config["sector_index_symbols"]
    }
    percentiles = relative_strength_percentiles({symbol: daily_histories[symbol] for symbol in symbols})
    candidates: list[dict[str, Any]] = []
    exits: list[dict[str, Any]] = []

    for symbol in symbols:
        candles = signal_histories[symbol]
        if not candles:
            raise ValueError(f"No market candles returned for {symbol}")
        if not daily_histories[symbol]:
            raise ValueError(f"No daily market candles returned for {symbol}")
        if symbol in state["positions"]:
            position = PaperPosition.from_dict(state["positions"][symbol])
            reason, exit_candle = _evaluate_position_history(
                position,
                candles,
                config,
                current_time=datetime.now(IST).replace(tzinfo=None),
            )
            if reason:
                exit_price = _exit_reference(position, exit_candle, reason)
                pnl_pct = (exit_price / position.entry_price - 1) * 100
                closed = {
                    "symbol": symbol,
                    "entry_time": position.entry_time,
                    "exit_time": exit_candle.timestamp.isoformat(),
                    "exit_reason": reason,
                    "exit_reference": round(exit_price, 4),
                    "pnl_pct": round(pnl_pct, 4),
                }
                state["closed_trades"].append(closed)
                del state["positions"][symbol]
                exits.append(closed)
            else:
                state["positions"][symbol] = position
            continue

        sector_index = sector_by_symbol[symbol]
        candidate = scan_symbol(
            symbol=symbol,
            candles=candles,
            daily_candles=daily_histories[symbol],
            config=config,
            rs_percentile=percentiles.get(symbol, 0.0),
            sector_ok=sector_eligibility[sector_index],
            bearish_market=market_bearish,
            rolling_win_rate_pct=win_rate,
            table_path=TABLE_PATH,
        )
        if candidate:
            state["positions"][symbol] = PaperPosition.from_dict(
                {
                    "symbol": candidate["symbol"],
                    "entry_time": candidate["timestamp"],
                    "entry_price": candidate["entry_reference"],
                    "initial_stop": candidate["initial_stop"],
                    "target_price": candidate["target"],
                    "high_water": candidate["entry_reference"],
                    "session_date": candles[-1].timestamp.date().isoformat(),
                    "session_low": candles[-1].low,
                    "last_evaluated_timestamp": candidate["timestamp"],
                }
            )
            candidates.append(candidate)

    state["closed_trades"] = state["closed_trades"][-max(config["rolling_win_rate_trades"] * 4, 100):]
    save_paper_state(config["paper_state_path"], state)
    return {
        "mode": "scan_only",
        "live_orders_enabled": False,
        "universe_size": len(symbols),
        "market_regime": "bearish" if market_bearish else "not_bearish",
        "rolling_win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
        "signals": candidates,
        "paper_exits": exits,
        "open_paper_positions": len(state["positions"]),
    }


def main() -> int:
    raw_config = os.environ.get("TRADER_CONFIG_JSON")
    if not raw_config:
        print("TRADER_CONFIG_JSON is required; see strategy_config.example.json", file=sys.stderr)
        return 2
    try:
        config = load_config(raw_config)
        report = run_scan(config, AngelOneMarketData())
    except Exception as exc:
        print(f"Scanner failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
