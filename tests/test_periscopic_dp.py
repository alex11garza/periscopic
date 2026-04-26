"""Tests for the Periscopic DP table-size estimator stage."""

import pytest
import periscopic as p


# ---------------------------------------------------------------------------
# laplace_sample
# ---------------------------------------------------------------------------

class TestLaplaceSample:
    def test_returns_non_negative(self):
        for _ in range(100):
            assert p.laplace_sample(1.0) >= 0

    def test_invalid_scale_raises(self):
        with pytest.raises(ValueError):
            p.laplace_sample(0.0)
        with pytest.raises(ValueError):
            p.laplace_sample(-1.0)

    def test_larger_scale_larger_average(self):
        small = sum(p.laplace_sample(0.1) for _ in range(500)) / 500
        large = sum(p.laplace_sample(10.0) for _ in range(500)) / 500
        assert large > small


# ---------------------------------------------------------------------------
# noisy_count
# ---------------------------------------------------------------------------

class TestNoisyCount:
    def test_returns_non_negative(self):
        for _ in range(100):
            assert p.noisy_count(50, 1.0) >= 0

    def test_zero_count_non_negative(self):
        for _ in range(100):
            assert p.noisy_count(0, 1.0) >= 0

    def test_invalid_epsilon_raises(self):
        with pytest.raises(ValueError):
            p.noisy_count(100, 0.0)

    def test_returns_integer(self):
        result = p.noisy_count(100, 1.0)
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TableSizeEstimator
# ---------------------------------------------------------------------------

class TestTableSizeEstimator:
    def test_construction(self):
        est = p.TableSizeEstimator(0.5)
        assert est.epsilon == 0.5
        assert est.table_count == 0

    def test_invalid_epsilon_raises(self):
        with pytest.raises(ValueError):
            p.TableSizeEstimator(0.0)
        with pytest.raises(ValueError):
            p.TableSizeEstimator(-1.0)

    def test_load_and_count(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100), ("orders", 200)])
        assert est.table_count == 2

    def test_noisy_size_returns_non_negative(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100)])
        assert est.noisy_size("users") >= 0

    def test_noisy_size_unknown_table_returns_minus_one(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100)])
        assert est.noisy_size("nonexistent") == -1

    def test_noisy_size_case_insensitive(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("Users", 100)])
        assert est.noisy_size("users") >= 0
        assert est.noisy_size("USERS") >= 0

    def test_load_replaces_previous(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("a", 10), ("b", 20), ("c", 30)])
        assert est.table_count == 3
        est.load([("x", 100)])
        assert est.table_count == 1
        assert est.noisy_size("a") == -1

    def test_heap_snapshot_sorted(self):
        est = p.TableSizeEstimator(100.0)  # high epsilon = low noise
        est.load([("big", 10000), ("small", 1), ("medium", 500)])
        snap = est.heap_snapshot()
        assert len(snap) == 3
        sizes = [entry.noisy_size for entry in snap]
        assert sizes == sorted(sizes)

    def test_heap_snapshot_has_table_names(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100), ("orders", 200)])
        snap = est.heap_snapshot()
        names = {entry.table_name for entry in snap}
        assert names == {"users", "orders"}


# ---------------------------------------------------------------------------
# join_order
# ---------------------------------------------------------------------------

class TestJoinOrder:
    def test_orders_smallest_first(self):
        """With very high epsilon (low noise), order should track true sizes."""
        est = p.TableSizeEstimator(1000.0)
        est.load([("big", 10000), ("small", 1), ("medium", 500)])
        order = est.join_order(["big", "small", "medium"])
        assert order[0] == "small"
        assert order[-1] == "big"

    def test_unknown_tables_last(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100)])
        order = est.join_order(["users", "unknown_table"])
        assert order[-1] == "unknown_table"

    def test_returns_same_tables(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("a", 10), ("b", 20)])
        order = est.join_order(["b", "a"])
        assert sorted(order) == ["a", "b"]

    def test_single_table(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100)])
        assert est.join_order(["users"]) == ["users"]

    def test_empty_list(self):
        est = p.TableSizeEstimator(1.0)
        est.load([("users", 100)])
        assert est.join_order([]) == []


# ---------------------------------------------------------------------------
# periscopic() convenience function
# ---------------------------------------------------------------------------

class TestPeriscopicFunction:
    def test_returns_list(self):
        result = p.periscopic(
            ["orders", "users"],
            catalog=[("users", 100), ("orders", 200)],
            epsilon=1.0,
        )
        assert isinstance(result, list)
        assert sorted(result) == ["orders", "users"]

    def test_high_epsilon_respects_order(self):
        result = p.periscopic(
            ["big", "small"],
            catalog=[("big", 10000), ("small", 1)],
            epsilon=1000.0,
        )
        assert result[0] == "small"


# ---------------------------------------------------------------------------
# estimator() convenience function
# ---------------------------------------------------------------------------

class TestEstimatorFunction:
    def test_returns_estimator(self):
        est = p.estimator([("users", 100)], epsilon=0.5)
        assert isinstance(est, p.TableSizeEstimator)
        assert est.table_count == 1

    def test_reusable(self):
        est = p.estimator(
            [("a", 10), ("b", 20), ("c", 30)], epsilon=1.0
        )
        r1 = est.join_order(["a", "b"])
        r2 = est.join_order(["b", "c"])
        assert sorted(r1) == ["a", "b"]
        assert sorted(r2) == ["b", "c"]
