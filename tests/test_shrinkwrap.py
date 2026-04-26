"""Tests for the ShrinkWrap structural padding stage."""

import pytest
import periscopic as p


# ---------------------------------------------------------------------------
# shrinkwrap() — level-based padding
# ---------------------------------------------------------------------------

class TestShrinkwrapPaddingOff:
    """When padding=False, the query is returned unchanged."""

    def test_returns_unchanged(self):
        sql = "SELECT * FROM users"
        assert p.shrinkwrap(sql, padding=False) == sql

    def test_pad_level_ignored_when_off(self):
        sql = "SELECT * FROM users"
        assert p.shrinkwrap(sql, padding=False, pad_level=3) == sql


class TestShrinkwrapLevel1:
    """Level 1 applies comment wrapper only."""

    def test_comment_wrapper_applied(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=1)
        assert "-- shrinkwrap padding" in result
        assert "-- end padding" in result
        assert sql in result

    def test_no_column_pad_at_level_1(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=1)
        assert "pad_col" not in result


class TestShrinkwrapLevel2:
    """Level 2 adds column, aggregate, CTE, ORDER BY, and subquery pads."""

    def test_includes_comment_wrapper(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=2)
        assert "-- shrinkwrap padding" in result

    def test_select_star_gets_column_pad(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=2)
        assert "pad_col" in result

    def test_no_join_pad_at_level_2(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=2)
        assert "LEFT JOIN (SELECT 1 as dummy)" not in result


class TestShrinkwrapLevel3:
    """Level 3 adds the dummy LEFT JOIN on top of level 2."""

    def test_join_pad_present(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=3)
        assert "LEFT JOIN (SELECT 1 as dummy)" in result

    def test_also_has_column_pad(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql, padding=True, pad_level=3)
        assert "pad_col" in result


class TestShrinkwrapDefaultArgs:
    """Default padding=True, pad_level=2."""

    def test_default_pads(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap(sql)
        assert "-- shrinkwrap padding" in result
        assert "pad_col" in result


# ---------------------------------------------------------------------------
# shrinkwrap_pad() — individual named pads
# ---------------------------------------------------------------------------

class TestShrinkwrapPadQuery:
    def test_wraps_with_comments(self):
        sql = "SELECT 1"
        result = p.shrinkwrap_pad(sql, "query")
        assert "-- shrinkwrap padding" in result
        assert "-- end padding" in result


class TestShrinkwrapPadColumn:
    def test_adds_dummy_column(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap_pad(sql, "column")
        assert "pad_col" in result

    def test_no_star_unchanged(self):
        sql = "SELECT name FROM users"
        result = p.shrinkwrap_pad(sql, "column")
        assert result == sql


class TestShrinkwrapPadAggregate:
    def test_adds_dummy_aggregate(self):
        sql = "SELECT AVG(salary) as avg_salary FROM employees"
        result = p.shrinkwrap_pad(sql, "aggregate")
        assert "SUM(0) as pad_agg" in result

    def test_no_avg_unchanged(self):
        sql = "SELECT name FROM employees"
        result = p.shrinkwrap_pad(sql, "aggregate")
        assert result == sql


class TestShrinkwrapPadCte:
    def test_prepends_dummy_cte(self):
        sql = "WITH sales AS (SELECT * FROM orders) SELECT * FROM sales"
        result = p.shrinkwrap_pad(sql, "cte")
        assert "dummy_cte" in result

    def test_no_with_unchanged(self):
        sql = "SELECT * FROM orders"
        result = p.shrinkwrap_pad(sql, "cte")
        assert result == sql


class TestShrinkwrapPadJoin:
    def test_appends_dummy_join(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap_pad(sql, "join")
        assert "LEFT JOIN (SELECT 1 as dummy) sw ON 1=1" in result


class TestShrinkwrapPadOrderby:
    def test_prepends_dummy_orderby(self):
        sql = "SELECT * FROM users ORDER BY name"
        result = p.shrinkwrap_pad(sql, "orderby")
        assert "ORDER BY 0 /* shrinkwrap */, name" in result

    def test_no_orderby_unchanged(self):
        sql = "SELECT * FROM users"
        result = p.shrinkwrap_pad(sql, "orderby")
        assert result == sql


class TestShrinkwrapPadSubquery:
    def test_injects_into_subquery(self):
        sql = "SELECT * FROM (SELECT AVG(price) FROM products) sub"
        result = p.shrinkwrap_pad(sql, "subquery")
        assert "0 as pad_col" in result


class TestShrinkwrapPadInsert:
    def test_inserts_dummy_column(self):
        sql = "INSERT INTO users (name) VALUES ('Alice')"
        result = p.shrinkwrap_pad(sql, "insert")
        assert "pad_col" in result


class TestShrinkwrapPadUpdate:
    def test_prepends_dummy_set(self):
        sql = "UPDATE users SET name = 'Bob' WHERE id = 1"
        result = p.shrinkwrap_pad(sql, "update")
        assert "pad_col = 0" in result


class TestShrinkwrapPadDelete:
    def test_prepends_dummy_where(self):
        sql = "DELETE FROM users WHERE id = 1"
        result = p.shrinkwrap_pad(sql, "delete")
        assert "1=1 /* shrinkwrap */ AND" in result


class TestShrinkwrapPadInvalid:
    def test_unknown_pad_raises(self):
        with pytest.raises(ValueError, match="Unknown pad"):
            p.shrinkwrap_pad("SELECT 1", "nonexistent")
