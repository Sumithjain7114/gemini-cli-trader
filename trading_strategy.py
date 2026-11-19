"""Signal generation and paper risk management; this module never places orders."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PaperPosition:
    symbol: str
    entry_time: str
    entry_price: float
    initial_stop: float
    target_price: float
    high_water: float
    target_reached: bool = False
    trailing_stop: float | None = None
    session_date: str | None = None
    session_low: float | None = None
    last_evaluated_timestamp: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperPosition":
        return cls(**data)


def load_config(raw: str) -> dict[str, Any]:
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"TRADER_CONFIG_JSON is not valid JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("TRADER_CONFIG_JSON must contain a JSON object")

    required = (
        "candle_interval",
        "daily_history_days",
        "signal_history_days",
        "rsi_period",
        "volume_average_period",
        "breakout_lookback",
        "support_lookback",
        "pullback_support_tolerance_pct",
        "stop_buffer_pct",
        "target_r_multiple",
        "trailing_distance_pct",
        "bear_market_stop_tighten_pct",
        "market_index_symbol",
        "market_200dma_period",
        "sector_index_period",
        "sector_index_by_industry",
        "sector_index_symbols",
        "institutional_override_signals",
        "minervini",
        "nifty500_csv_url",
        "paper_state_path",
        "rolling_win_rate_trades",
        "eod_exit_time",
        "exit_on_intraday_low",
        "volume",
    )
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing required strategy settings: {', '.join(missing)}")
    numeric_settings = (
        "daily_history_days",
        "signal_history_days",
        "rsi_period",
        "volume_average_period",
        "breakout_lookback",
        "support_lookback",
        "pullback_support_tolerance_pct",
        "stop_buffer_pct",
        "target_r_multiple",
        "trailing_distance_pct",
        "bear_market_stop_tighten_pct",
        "market_200dma_period",
        "sector_index_period",
        "rolling_win_rate_trades",
    )
    unset = [key for key in numeric_settings if config[key] is None]
    if unset:
        raise ValueError(f"Set required strategy values before running: {', '.join(unset)}")
    if config["candle_interval"] not in {"ONE_DAY", "FIVE_MINUTE", "FIFTEEN_MINUTE"}:
        raise ValueError("Set candle_interval to ONE_DAY, FIVE_MINUTE, or FIFTEEN_MINUTE")
    float_settings = (
        "pullback_support_tolerance_pct",
        "stop_buffer_pct",
        "target_r_multiple",
        "trailing_distance_pct",
        "bear_market_stop_tighten_pct",
    )
    for key in float_settings:
        if not isinstance(config[key], (int, float)) or isinstance(config[key], bool) or not math.isfinite(config[key]):
            raise ValueError(f"{key} must be a finite number")
    if not 0 <= config["stop_buffer_pct"] < 100:
        raise ValueError("stop_buffer_pct must be in [0, 100)")
    if config["target_r_multiple"] < 2:
        raise ValueError("target_r_multiple must be at least 2 for the required 1:2 reward/risk")
    if not 0 < config["trailing_distance_pct"] < 100:
        raise ValueError("trailing_distance_pct must be in (0, 100)")
    if config["pullback_support_tolerance_pct"] < 0:
        raise ValueError("pullback_support_tolerance_pct must be non-negative")
    if config["daily_history_days"] < 400:
        raise ValueError("daily_history_days must be at least 400 to supply a 252-session trend history")
    if config["candle_interval"] == "ONE_DAY" and config["exit_on_intraday_low"]:
        raise ValueError("Set exit_on_intraday_low to false when candle_interval is ONE_DAY")
    if not isinstance(config["exit_on_intraday_low"], bool):
        raise ValueError("exit_on_intraday_low must be true or false")
    if config["market_200dma_period"] != 200 or config["sector_index_period"] != 200:
        raise ValueError("Market and sector trend filters must use the required 200-DMA")
    if config["paper_state_path"] != "paper_state.json":
        raise ValueError("paper_state_path must be paper_state.json so workflow runs can persist paper positions")
    try:
        time.fromisoformat(config["eod_exit_time"])
    except (TypeError, ValueError) as exc:
        raise ValueError("eod_exit_time must be a local market time such as 15:20") from exc
    if not 0 <= config["bear_market_stop_tighten_pct"] < 100:
        raise ValueError("bear_market_stop_tighten_pct must be in [0, 100)")
    for key in ("daily_history_days", "signal_history_days", "rsi_period", "volume_average_period", "breakout_lookback", "support_lookback", "sector_index_period", "market_200dma_period", "rolling_win_rate_trades"):
        if not isinstance(config[key], int) or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    volume = config["volume"]
    for key in ("pocket_pivot_lookback", "average_period", "bull_snort_multiple", "bull_snort_close_within_pct"):
        if key not in volume:
            raise ValueError(f"Missing required volume setting: {key}")
        if volume[key] is None:
            raise ValueError(f"Set required volume setting: volume.{key}")
    for key in ("pocket_pivot_lookback", "average_period"):
        if not isinstance(volume[key], int) or volume[key] < 1:
            raise ValueError(f"volume.{key} must be a positive integer")
    if (
        not isinstance(volume["bull_snort_multiple"], (int, float))
        or not math.isfinite(volume["bull_snort_multiple"])
        or volume["bull_snort_multiple"] < 1
    ):
        raise ValueError("volume.bull_snort_multiple must be at least 1")
    if (
        not isinstance(volume["bull_snort_close_within_pct"], (int, float))
        or not math.isfinite(volume["bull_snort_close_within_pct"])
        or not 1 <= volume["bull_snort_close_within_pct"] <= 100
    ):
        raise ValueError("volume.bull_snort_close_within_pct must be in [1, 100]")
    minervini = config["minervini"]
    for key in ("fast_ma_period", "mid_ma_period", "long_ma_period", "trend_lookback", "min_200dma_rise_pct", "min_above_52w_low_pct", "max_below_52w_high_pct", "min_rs_percentile"):
        if key not in minervini:
            raise ValueError(f"Missing required Minervini setting: {key}")
        if minervini[key] is None:
            raise ValueError(f"Set required Minervini value: minervini.{key}")
    for key in ("fast_ma_period", "mid_ma_period", "long_ma_period", "trend_lookback"):
        if not isinstance(minervini[key], int) or minervini[key] < 1:
            raise ValueError(f"minervini.{key} must be a positive integer")
    for key in ("min_200dma_rise_pct", "min_above_52w_low_pct", "max_below_52w_high_pct", "min_rs_percentile"):
        if not isinstance(minervini[key], (int, float)) or not math.isfinite(minervini[key]):
            raise ValueError(f"minervini.{key} must be a finite number")
    if not 0 <= minervini["min_rs_percentile"] <= 100:
        raise ValueError("minervini.min_rs_percentile must be in [0, 100]")
    if not config["sector_index_by_industry"]:
        raise ValueError("sector_index_by_industry must map every Nifty 500 industry to a sector index")
    if not config["sector_index_symbols"]:
        raise ValueError("sector_index_symbols must list the configured NSE sector-index symbols")
    if any(not isinstance(value, str) or not value.strip() for value in config["sector_index_by_industry"].values()):
        raise ValueError("Every sector_index_by_industry value must be a non-empty symbol")
    if any(not isinstance(value, str) or not value.strip() for value in config["sector_index_symbols"]):
        raise ValueError("Every sector_index_symbols entry must be a non-empty symbol")
    if not isinstance(config["market_index_symbol"], str) or not config["market_index_symbol"].strip():
        raise ValueError("market_index_symbol must be a non-empty symbol")
    if any(signal not in {"pocket_pivot", "bull_snort", "high_up_volume"} for signal in config["institutional_override_signals"]):
        raise ValueError("institutional_override_signals may contain pocket_pivot, bull_snort, or high_up_volume")
    if not isinstance(config["sector_index_by_industry"], dict):
        raise ValueError("sector_index_by_industry must be a JSON object")
    if not isinstance(config["sector_index_symbols"], list):
        raise ValueError("sector_index_symbols must be a JSON array")
    if not isinstance(config["institutional_override_signals"], list):
        raise ValueError("institutional_override_signals must be a JSON array")
    return config


def simple_moving_average(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    for index in range(period - 1, len(values)):
        result[index] = sum(values[index - period + 1:index + 1]) / period
    return result


def relative_strength_index(closes: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result
    initial_changes = [closes[i] - closes[i - 1] for i in range(1, period + 1)]
    average_gain = sum(max(change, 0) for change in initial_changes) / period
    average_loss = sum(max(-change, 0) for change in initial_changes) / period
    result[period] = 100.0 if average_loss == 0 else 100.0 - 100.0 / (1.0 + average_gain / average_loss)
    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        average_gain = (average_gain * (period - 1) + max(change, 0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0)) / period
        result[index] = 100.0 if average_loss == 0 else 100.0 - 100.0 / (1.0 + average_gain / average_loss)
    return result


def pine_volume_signals(candles: list[Candle], settings: dict[str, Any]) -> set[str]:
    if len(candles) < 2:
        return set()
    current = candles[-1]
    previous = candles[-2]
    volumes = [c.volume for c in candles]
    average_period = settings["average_period"]
    if len(volumes) < average_period:
        return set()
    avg_volume = sum(volumes[-average_period:]) / average_period
    signals: set[str] = set()
    up_day = current.close > previous.close
    down_volumes = [
        c.volume if c.close < candles[i - 1].close else 0.0
        for i, c in enumerate(candles)
        if i > 0
    ]
    lookback = settings["pocket_pivot_lookback"]
    if up_day and len(down_volumes) > lookback and current.volume > max(down_volumes[-lookback - 1:-1]):
        signals.add("pocket_pivot")
    if up_day and current.volume > avg_volume:
        signals.add("high_up_volume")
    bar_range = current.high - current.low
    close_from_high_pct = ((current.high - current.close) / bar_range * 100) if bar_range > 0 else 100.0
    if (
        up_day
        and current.volume >= avg_volume * settings["bull_snort_multiple"]
        and close_from_high_pct <= settings["bull_snort_close_within_pct"]
    ):
        signals.add("bull_snort")
    return signals


def minervini_pass(
    candles: list[Candle],
    relative_strength_percentile: float,
    settings: dict[str, Any],
) -> bool:
    closes = [c.close for c in candles]
    fast_period = settings["fast_ma_period"]
    mid_period = settings["mid_ma_period"]
    long_period = settings["long_ma_period"]
    trend_lookback = settings["trend_lookback"]
    if len(candles) < max(long_period + trend_lookback, 252):
        return False
    fast = simple_moving_average(closes, fast_period)
    mid = simple_moving_average(closes, mid_period)
    long = simple_moving_average(closes, long_period)
    index = len(candles) - 1
    if fast[index] is None or mid[index] is None or long[index] is None or long[index - trend_lookback] is None:
        return False
    last = candles[-1].close
    low_52 = min(c.low for c in candles[-252:])
    high_52 = max(c.high for c in candles[-252:])
    rise_pct = (long[index] / long[index - trend_lookback] - 1.0) * 100
    above_low_pct = (last / low_52 - 1.0) * 100 if low_52 else 0.0
    below_high_pct = (high_52 - last) / high_52 * 100 if high_52 else 100.0
    return all(
        (
            last > fast[index] > mid[index] > long[index],
            rise_pct >= settings["min_200dma_rise_pct"],
            above_low_pct >= settings["min_above_52w_low_pct"],
            below_high_pct <= settings["max_below_52w_high_pct"],
            relative_strength_percentile >= settings["min_rs_percentile"],
        )
    )


def relative_strength_percentiles(histories: dict[str, list[Candle]]) -> dict[str, float]:
    performance: dict[str, float] = {}
    for symbol, candles in histories.items():
        if len(candles) >= 252 and candles[-252].close > 0:
            performance[symbol] = candles[-1].close / candles[-252].close - 1.0
    sorted_symbols = sorted(performance, key=performance.get)
    denominator = max(len(sorted_symbols) - 1, 1)
    return {symbol: rank / denominator * 100 for rank, symbol in enumerate(sorted_symbols)}


def table_expectancy(stop_pct: float, win_rate_pct: float, table_path: str | Path) -> float | None:
    """Interpolate the supplied table's 2:1 rows; return None outside its win-rate range."""
    if win_rate_pct < 30 or win_rate_pct > 50:
        return None
    rows: list[tuple[float, float, float, float]] = []
    with Path(table_path).open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append((
                float(row["loss_pct"]),
                float(row["win_30_pct"]),
                float(row["win_40_pct"]),
                float(row["win_50_pct"]),
            ))
    if not rows:
        raise ValueError("Risk/reward expectancy table is empty")
    rows.sort(key=lambda row: row[0])
    if stop_pct < rows[0][0] or stop_pct > rows[-1][0]:
        return None
    lower = max((row for row in rows if row[0] <= stop_pct), key=lambda row: row[0])
    upper = min((row for row in rows if row[0] >= stop_pct), key=lambda row: row[0])

    def at_win_rate(row: tuple[float, float, float, float]) -> float:
        low_value, high_value = (row[1], row[2]) if win_rate_pct <= 40 else (row[2], row[3])
        low_rate, high_rate = (30.0, 40.0) if win_rate_pct <= 40 else (40.0, 50.0)
        return low_value + (high_value - low_value) * (win_rate_pct - low_rate) / (high_rate - low_rate)

    lower_value = at_win_rate(lower)
    upper_value = at_win_rate(upper)
    if lower[0] == upper[0]:
        return lower_value
    fraction = (stop_pct - lower[0]) / (upper[0] - lower[0])
    return lower_value + (upper_value - lower_value) * fraction


def scan_symbol(
    symbol: str,
    candles: list[Candle],
    daily_candles: list[Candle],
    config: dict[str, Any],
    rs_percentile: float,
    sector_ok: bool,
    bearish_market: bool,
    rolling_win_rate_pct: float | None,
    table_path: str | Path,
) -> dict[str, Any] | None:
    required = max(
        config["rsi_period"] + 1,
        config["volume_average_period"],
        config["breakout_lookback"] + 1,
        config["support_lookback"] + 1,
    )
    if len(candles) < required:
        return None
    settings = config["volume"]
    if not minervini_pass(daily_candles, rs_percentile, config["minervini"]):
        return None

    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    rsi = relative_strength_index(closes, config["rsi_period"])[-1]
    if rsi is None or rsi <= 60:
        return None

    last = candles[-1]
    prior = candles[:-1]
    resistance = max(c.high for c in prior[-config["breakout_lookback"]:])
    support_bars = prior[-config["support_lookback"]:]
    support = min(c.low for c in support_bars)
    avg_volume = sum(volumes[-config["volume_average_period"]:]) / config["volume_average_period"]
    volume_signals = pine_volume_signals(candles, settings)
    is_breakout = last.close > resistance and last.volume > avg_volume
    tolerance = config["pullback_support_tolerance_pct"] / 100
    is_fast_pullback = (
        last.low <= support * (1 + tolerance)
        and last.close > support
        and last.close > prior[-1].close
    )
    setup = "breakout" if is_breakout else "fast_pullback" if is_fast_pullback else None
    if setup is None:
        return None
    if setup == "breakout" and last.volume <= avg_volume:
        return None
    required_volume_signals = set(config["institutional_override_signals"])
    institutional_pattern = bool(volume_signals & required_volume_signals)
    if not sector_ok and not institutional_pattern:
        return None

    stop = support * (1 - config["stop_buffer_pct"] / 100)
    if bearish_market:
        stop = last.close - (last.close - stop) * (1 - config["bear_market_stop_tighten_pct"] / 100)
    if stop <= 0 or stop >= last.close:
        return None
    risk = last.close - stop
    risk_reward = config["target_r_multiple"]
    if risk_reward < 2:
        raise ValueError("target_r_multiple must be at least 2")
    target = last.close + risk * risk_reward
    stop_pct = risk / last.close * 100
    expectancy = table_expectancy(stop_pct, rolling_win_rate_pct, table_path) if rolling_win_rate_pct is not None else None
    return {
        "symbol": symbol,
        "timestamp": last.timestamp.isoformat(),
        "setup": setup,
        "entry_reference": round(last.close, 4),
        "initial_stop": round(stop, 4),
        "target": round(target, 4),
        "risk_reward": risk_reward,
        "rsi": round(rsi, 2),
        "volume": last.volume,
        "average_volume": round(avg_volume, 2),
        "volume_signals": sorted(volume_signals),
        "institutional_pattern": institutional_pattern,
        "bearish_market_stop_tightened": bearish_market,
        "expectancy_table_pct": round(expectancy, 2) if expectancy is not None else None,
    }


def create_paper_position(candidate: dict[str, Any]) -> PaperPosition:
    return PaperPosition(
        symbol=candidate["symbol"],
        entry_time=candidate["timestamp"],
        entry_price=candidate["entry_reference"],
        initial_stop=candidate["initial_stop"],
        target_price=candidate["target"],
        high_water=candidate["entry_reference"],
    )


def evaluate_paper_position(
    position: PaperPosition,
    candle: Candle,
    config: dict[str, Any],
    current_time: datetime | None = None,
) -> str | None:
    if position.target_reached:
        candidate_trail = position.high_water * (1 - config["trailing_distance_pct"] / 100)
        position.trailing_stop = max(position.trailing_stop or position.initial_stop, candidate_trail)
    effective_stop = position.trailing_stop if position.target_reached else position.initial_stop

    # Conservative ordering: if a bar crosses both stop and target, record the stop first.
    if candle.low <= effective_stop:
        return "trailing_stop" if position.target_reached else "support_stop"
    current_date = candle.timestamp.date().isoformat()
    if position.session_date != current_date:
        position.session_date = current_date
        position.session_low = candle.low
    elif config["exit_on_intraday_low"] and position.session_low is not None and candle.low < position.session_low:
        return "intraday_low"
    else:
        position.session_low = min(position.session_low or candle.low, candle.low)
    position.high_water = max(position.high_water, candle.high)
    if candle.high >= position.target_price:
        position.target_reached = True
        candidate_trail = position.high_water * (1 - config["trailing_distance_pct"] / 100)
        position.trailing_stop = max(position.initial_stop, candidate_trail)

    exit_time = time.fromisoformat(config["eod_exit_time"])
    observed_time = current_time.time() if current_time is not None else candle.timestamp.time()
    if observed_time >= exit_time:
        return "end_of_day"
    return None


def load_paper_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return {"positions": {}, "closed_trades": []}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read paper state at {state_path}: {exc}") from exc
    if not isinstance(state, dict) or not isinstance(state.get("positions"), dict) or not isinstance(state.get("closed_trades"), list):
        raise ValueError(f"Invalid paper state structure in {state_path}")
    return state


def save_paper_state(path: str | Path, state: dict[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "positions": {
            symbol: asdict(position) if isinstance(position, PaperPosition) else position
            for symbol, position in state["positions"].items()
        },
        "closed_trades": state["closed_trades"],
    }
    state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def recent_win_rate(state: dict[str, Any], window: int) -> float | None:
    trades = state["closed_trades"][-window:]
    if not trades:
        return None
    winners = sum(1 for trade in trades if trade["pnl_pct"] > 0)
    return winners / len(trades) * 100
