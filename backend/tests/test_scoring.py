"""Pure-function unit tests for the scoring formula building blocks that don't
need a database: period math, goal progress, and the weighted total.
"""

from __future__ import annotations

import unittest
from datetime import date
from types import SimpleNamespace

from app.services.scoring import _goal_progress, _weighted_total, current_period, period_bounds


class PeriodTest(unittest.TestCase):
    def test_current_period_format(self) -> None:
        self.assertEqual(current_period(date(2026, 7, 12)), "2026-Q3")
        self.assertEqual(current_period(date(2026, 1, 1)), "2026-Q1")
        self.assertEqual(current_period(date(2026, 12, 31)), "2026-Q4")

    def test_period_bounds_cover_full_quarter(self) -> None:
        self.assertEqual(period_bounds("2026-Q1"), (date(2026, 1, 1), date(2026, 3, 31)))
        self.assertEqual(period_bounds("2026-Q2"), (date(2026, 4, 1), date(2026, 6, 30)))
        self.assertEqual(period_bounds("2026-Q4"), (date(2026, 10, 1), date(2026, 12, 31)))


def _goal(target=None, baseline=None, current=None):
    return SimpleNamespace(target_value=target, baseline_value=baseline, current_value=current)


class GoalProgressTest(unittest.TestCase):
    def test_halfway_progress(self) -> None:
        # baseline 1710 -> target 1282 (reduction goal), currently at 1496 (halfway).
        g = _goal(target=1282, baseline=1710, current=1496)
        self.assertAlmostEqual(_goal_progress(g), 0.5, places=3)

    def test_goal_exceeded_clamps_to_1(self) -> None:
        g = _goal(target=1282, baseline=1710, current=1000)
        self.assertEqual(_goal_progress(g), 1.0)

    def test_goal_regressed_clamps_to_0(self) -> None:
        g = _goal(target=1282, baseline=1710, current=2000)
        self.assertEqual(_goal_progress(g), 0.0)

    def test_increasing_target_goal(self) -> None:
        # renewable share 32 -> 80, currently at 56 (halfway).
        g = _goal(target=80, baseline=32, current=56)
        self.assertAlmostEqual(_goal_progress(g), 0.5, places=3)

    def test_missing_baseline_defaults_to_zero(self) -> None:
        g = _goal(target=100, baseline=None, current=50)
        self.assertAlmostEqual(_goal_progress(g), 0.5, places=3)

    def test_no_target_is_zero(self) -> None:
        g = _goal(target=None, baseline=0, current=50)
        self.assertEqual(_goal_progress(g), 0.0)


class WeightedTotalTest(unittest.TestCase):
    def test_default_weights(self) -> None:
        # 40/30/30 of (80, 70, 60) = 32 + 21 + 18 = 71
        total = _weighted_total(80, 70, 60, {"E": 40, "S": 30, "G": 30})
        self.assertAlmostEqual(total, 71.0, places=2)

    def test_custom_weights(self) -> None:
        total = _weighted_total(100, 0, 0, {"E": 50, "S": 25, "G": 25})
        self.assertAlmostEqual(total, 50.0, places=2)

    def test_clamped_to_100(self) -> None:
        total = _weighted_total(100, 100, 100, {"E": 40, "S": 30, "G": 30})
        self.assertLessEqual(total, 100.0)


if __name__ == "__main__":
    unittest.main()
