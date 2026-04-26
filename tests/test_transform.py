"""Tests for the full Periscopic transform() pipeline."""

import periscopic as p


class TestTransformReturnShape:
    """transform() always returns a dict with the expected keys."""

    def test_keys_present(self):
        result = p.transform("SELECT salary, name FROM employees")
        assert set(result.keys()) == {"original", "orq", "join_order", "shrinkwrap"}

    def test_original_preserved(self):
        sql = "SELECT salary, name FROM employees"
        result = p.transform(sql)
        assert result["original"] == sql


class TestTransformOrqStage:
    def test_columns_sorted(self):
        sql = "SELECT salary, name FROM employees"
        result = p.transform(sql)
        assert result["orq"] == "SELECT name, salary FROM employees"


class TestTransformNoCatalog:
    """Without a catalog, join_order should be None."""

    def test_join_order_is_none(self):
        result = p.transform("SELECT * FROM users")
        assert result["join_order"] is None

    def test_shrinkwrap_still_applied(self):
        result = p.transform("SELECT * FROM users")
        assert "-- shrinkwrap padding" in result["shrinkwrap"]


class TestTransformWithCatalog:
    """With a catalog, join_order is computed via DP."""

    def test_join_order_returned(self):
        result = p.transform(
            "SELECT name, salary FROM orders JOIN users ON 1=1",
            catalog=[("users", 100), ("orders", 200)],
            epsilon=1.0,
        )
        assert result["join_order"] is not None
        assert isinstance(result["join_order"], list)
        assert sorted(result["join_order"]) == ["orders", "users"]

    def test_high_epsilon_order(self):
        result = p.transform(
            "SELECT * FROM big JOIN small ON 1=1",
            catalog=[("big", 10000), ("small", 1)],
            epsilon=1000.0,
        )
        assert result["join_order"][0] == "small"


class TestTransformPaddingOff:
    def test_no_padding(self):
        sql = "SELECT salary, name FROM employees"
        result = p.transform(sql, padding=False)
        # shrinkwrap output should just be the ORQ output (no padding added)
        assert result["shrinkwrap"] == result["orq"]

    def test_no_comment_wrapper(self):
        result = p.transform("SELECT * FROM users", padding=False)
        assert "-- shrinkwrap padding" not in result["shrinkwrap"]


class TestTransformPadLevels:
    def test_level_1_no_column_pad(self):
        result = p.transform("SELECT * FROM users", pad_level=1)
        assert "-- shrinkwrap padding" in result["shrinkwrap"]
        assert "pad_col" not in result["shrinkwrap"]

    def test_level_3_has_join_pad(self):
        result = p.transform("SELECT * FROM users", pad_level=3)
        assert "LEFT JOIN (SELECT 1 as dummy)" in result["shrinkwrap"]
