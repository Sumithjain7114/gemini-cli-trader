import json
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from angelone_data import AngelOneMarketData, load_nifty500_constituents
import live_cloud_trader
from trading_strategy import (
    Candle,
    PaperPosition,
    evaluate_paper_position,
    load_config,
    minervini_pass,
    pine_volume_signals,
    relative_strength_index,
    scan_symbol,
    table_expectancy,
)
from live_cloud_trader import _evaluate_position_history


ROOT = Path(__file__).resolve().parents[1]


def candles(count, start_price=100.0, volume=100.0):
    start = datetime(2026, 1, 1)
    return [
        Candle(
            timestamp=start + timedelta(days=index),
            open=start_price + index,
            high=start_price + index + 0.5,
            low=start_price + index - 0.5,
            close=start_price + index,
            volume=volume,
        )
        for index in range(count)
    ]


def config():
    return {
        "candle_interval": "FIVE_MINUTE",
        "daily_history_days": 500,
        "signal_history_days": 10,
        "rsi_period": 14,
        "volume_average_period": 20,
        "breakout_lookback": 20,
        "support_lookback": 10,
        "pullback_support_tolerance_pct": 1.0,
        "stop_buffer_pct": 1.0,
        "target_r_multiple": 2.0,
        "trailing_distance_pct": 10.0,
        "bear_market_stop_tighten_pct": 25.0,
        "market_index_symbol": "NIFTY 50",
        "market_200dma_period": 200,
        "sector_index_period": 200,
        "sector_index_by_industry": {"IT": "NIFTY IT"},
        "sector_index_symbols": ["NIFTY IT"],
        "institutional_override_signals": ["pocket_pivot", "bull_snort"],
        "minervini": {
            "fast_ma_period": 5,
            "mid_ma_period": 10,
            "long_ma_period": 20,
            "trend_lookback": 10,
            "min_200dma_rise_pct": 0.0,
            "min_above_52w_low_pct": 0.0,
            "max_below_52w_high_pct": 100.0,
            "min_rs_percentile": 0.0,
        },
        "nifty500_csv_url": "https://example.invalid/nifty.csv",
        "paper_state_path": "paper_state.json",
        "rolling_win_rate_trades": 20,
        "eod_exit_time": "15:20",
        "exit_on_intraday_low": True,
        "volume": {
            "average_period": 20,
            "pocket_pivot_lookback": 10,
            "bull_snort_multiple": 3.0,
            "bull_snort_close_within_pct": 35.0,
        },
    }


class TradingStrategyTests(unittest.TestCase):
    def test_rsi_is_unavailable_until_lookback_then_over_60_in_uptrend(self):
        values = relative_strength_index([float(i) for i in range(1, 20)], 14)
        self.assertIsNone(values[13])
        self.assertEqual(values[-1], 100.0)

    def test_attached_table_expectancy_interpolates_and_does_not_extrapolate(self):
        table = ROOT / "risk_reward_expectancy.csv"
        self.assertAlmostEqual(table_expectancy(2, 40, table), 3.63)
        self.assertAlmostEqual(table_expectancy(2, 35, table), 0.64)
        self.assertIsNone(table_expectancy(2, 25, table))
        self.assertIsNone(table_expectancy(51, 40, table))

    def test_pine_volume_port_detects_pocket_pivot_and_bull_snort(self):
        series = candles(51, volume=100)
        series[-2] = Candle(series[-2].timestamp, 149, 151, 148, 149, 150)
        series[-1] = Candle(series[-1].timestamp, 149, 153, 148, 152, 500)
        signals = pine_volume_signals(series, config()["volume"])
        self.assertIn("pocket_pivot", signals)
        self.assertIn("bull_snort", signals)
        self.assertIn("high_up_volume", signals)

    def test_minervini_template_and_breakout_require_rsi_volume_and_trend(self):
        daily = candles(260, volume=100)
        settings = config()["minervini"]
        self.assertTrue(minervini_pass(daily, 90, settings))

        signal = candles(50, start_price=100, volume=100)
        previous = signal[-1]
        signal[-1] = Candle(previous.timestamp, previous.close, previous.close + 4, previous.close - 1, previous.close + 3, 500)
        candidate = scan_symbol(
            "TEST",
            signal,
            daily,
            config(),
            rs_percentile=90,
            sector_ok=False,
            bearish_market=True,
            rolling_win_rate_pct=40,
            table_path=ROOT / "risk_reward_expectancy.csv",
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["setup"], "breakout")
        self.assertGreaterEqual(candidate["risk_reward"], 2)
        self.assertTrue(candidate["bearish_market_stop_tightened"])
        self.assertTrue(candidate["institutional_pattern"])
        no_override = config()
        no_override["institutional_override_signals"] = []
        self.assertIsNone(scan_symbol(
            "TEST",
            signal,
            daily,
            no_override,
            rs_percentile=90,
            sector_ok=False,
            bearish_market=False,
            rolling_win_rate_pct=40,
            table_path=ROOT / "risk_reward_expectancy.csv",
        ))

    def test_fast_pullback_requires_support_reclaim_and_places_stop_below_support(self):
        daily = candles(260, volume=100)
        signal = candles(50, volume=100)
        previous = signal[-2]
        support = min(c.low for c in signal[-11:-1])
        signal[-1] = Candle(
            signal[-1].timestamp,
            previous.close,
            previous.close + 0.4,
            support * 1.005,
            previous.close + 0.2,
            100,
        )
        candidate = scan_symbol(
            "TEST",
            signal,
            daily,
            config(),
            rs_percentile=90,
            sector_ok=True,
            bearish_market=False,
            rolling_win_rate_pct=None,
            table_path=ROOT / "risk_reward_expectancy.csv",
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["setup"], "fast_pullback")
        self.assertLess(candidate["initial_stop"], support)
        self.assertGreaterEqual(
            candidate["target"] - candidate["entry_reference"],
            2 * (candidate["entry_reference"] - candidate["initial_stop"]),
        )

    def test_target_activates_trailing_stop_and_trailing_exit(self):
        position = PaperPosition(
            symbol="TEST",
            entry_time="2026-10-30T10:00:00",
            entry_price=100,
            initial_stop=95,
            target_price=110,
            high_water=100,
        )
        cfg = config()
        first = Candle(datetime(2026, 10, 31, 10), 105, 112, 101, 110, 100)
        self.assertIsNone(evaluate_paper_position(position, first, cfg))
        self.assertTrue(position.target_reached)
        self.assertEqual(position.trailing_stop, 100.8)
        second = Candle(datetime(2026, 10, 31, 10, 5), 110, 113, 100.7, 101, 100)
        self.assertEqual(evaluate_paper_position(position, second, cfg), "trailing_stop")

    def test_eod_exit_uses_current_market_time(self):
        position = PaperPosition("TEST", "2026-10-31T10:00:00", 100, 95, 110, 100)
        candle = Candle(datetime(2026, 10, 31, 14, 55), 101, 102, 100, 101, 100)
        self.assertEqual(
            evaluate_paper_position(position, candle, config(), datetime(2026, 10, 31, 15, 21)),
            "end_of_day",
        )

    def test_intraday_new_low_exit(self):
        position = PaperPosition(
            "TEST",
            "2026-10-31T10:00:00",
            100,
            95,
            110,
            100,
            session_date="2026-10-31",
            session_low=100,
        )
        candle = Candle(datetime(2026, 10, 31, 10, 5), 100, 101, 99, 100, 100)
        self.assertEqual(evaluate_paper_position(position, candle, config()), "intraday_low")

    def test_position_replays_each_unseen_candle_for_stops(self):
        position = PaperPosition(
            "TEST",
            "2026-10-30T10:00:00",
            100,
            95,
            110,
            100,
            last_evaluated_timestamp="2026-10-30T10:00:00",
        )
        series = [
            Candle(datetime(2026, 10, 30, 10, 5), 100, 101, 96, 99, 100),
            Candle(datetime(2026, 10, 30, 10, 10), 99, 100, 94, 95, 100),
            Candle(datetime(2026, 10, 30, 10, 15), 95, 98, 94, 96, 100),
        ]
        reason, exit_candle = _evaluate_position_history(
            position, series, config(), datetime(2026, 10, 30, 10, 16)
        )
        self.assertEqual(reason, "support_stop")
        self.assertEqual(exit_candle.timestamp, series[1].timestamp)

    def test_configuration_rejects_reward_risk_below_two_to_one(self):
        cfg = config()
        cfg["target_r_multiple"] = 1.5
        with self.assertRaisesRegex(ValueError, "at least 2"):
            load_config(json.dumps(cfg))

    def test_constituent_loader_requires_and_reads_industry_mapping(self):
        csv_bytes = b"Symbol,Industry\nABC,Information Technology\n"
        with patch("angelone_data._download", return_value=csv_bytes):
            self.assertEqual(
                load_nifty500_constituents("https://example.invalid/nifty.csv"),
                [("ABC", "Information Technology")],
            )

    def test_market_adapter_requests_only_candles_and_surfaces_api_failures(self):
        env = {
            "ANGELONE_API_KEY": "test-key",
            "ANGELONE_CLIENT_CODE": "test-client",
            "ANGELONE_PIN": "test-pin",
            "ANGELONE_TOTP_SECRET": "test-secret",
            "ANGELONE_REQUEST_DELAY_SECONDS": "0",
        }

        class ReadOnlyFakeClient:
            def __init__(self, response):
                self.response = response
                self.params = None

            def getCandleData(self, params):
                self.params = params
                return self.response

        with patch.dict(os.environ, env, clear=False):
            market = AngelOneMarketData()
        client = ReadOnlyFakeClient({
            "status": True,
            "data": [["2026-10-31T09:15:00+05:30", "100", "102", "99", "101", "500"]],
        })
        market.client = client
        market._tokens = {("symbol", "ABC"): "123"}
        candles_result = market.candles("ABC", "FIVE_MINUTE", 5)
        self.assertEqual(candles_result[0].close, 101.0)
        self.assertEqual(client.params["symboltoken"], "123")
        self.assertFalse(hasattr(client, "placeOrder"))

        market.client = ReadOnlyFakeClient({"status": False, "message": "rate limited"})
        with self.assertRaisesRegex(RuntimeError, "rate limited"):
            market.candles("ABC", "FIVE_MINUTE", 5)

    def test_scan_report_is_signal_only_and_tracks_paper_candidate(self):
        daily = candles(260, volume=100)
        signal = candles(50, volume=100)
        previous = signal[-1]
        signal[-1] = Candle(
            previous.timestamp,
            previous.close,
            previous.close + 4,
            previous.close - 1,
            previous.close + 3,
            500,
        )

        class FakeMarket:
            logged_out = False

            def connect(self):
                pass

            def logout(self):
                self.logged_out = True

            def candles(self, symbol, interval, history_days):
                if symbol == "TEST" and interval != "ONE_DAY":
                    return signal
                return daily

        market = FakeMarket()
        with (
            patch("live_cloud_trader.load_nifty500_constituents", return_value=[("TEST", "IT")]),
            patch("live_cloud_trader.load_paper_state", return_value={"positions": {}, "closed_trades": []}),
            patch("live_cloud_trader.save_paper_state") as save_state,
        ):
            report = live_cloud_trader.run_scan(config(), market)
        self.assertTrue(market.logged_out)
        self.assertFalse(report["live_orders_enabled"])
        self.assertEqual(report["mode"], "scan_only")
        self.assertEqual(report["universe_size"], 1)
        self.assertEqual(report["signals"][0]["setup"], "breakout")
        save_state.assert_called_once()


if __name__ == "__main__":
    unittest.main()
