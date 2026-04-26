"""Tests for the ORQ (Order-Respecting Query) stage."""

import periscopic as p


class TestOrqBasic:
    """Column sorting on straightforward SELECT statements."""

    def test_sorts_columns_alphabetically(self):
        result = p.orq("SELECT salary, name, age FROM employees")
        assert result == "SELECT age, name, salary FROM employees"

    def test_single_column_unchanged(self):
        sql = "SELECT name FROM employees"
        assert p.orq(sql) == sql

    def test_select_star_unchanged(self):
        sql = "SELECT * FROM employees"
        assert p.orq(sql) == sql

    def test_already_sorted(self):
        sql = "SELECT age, name, salary FROM employees"
        assert p.orq(sql) == sql

    def test_two_columns(self):
        result = p.orq("SELECT z_col, a_col FROM t")
        assert result == "SELECT a_col, z_col FROM t"


class TestOrqCaseInsensitive:
    """Sorting is case-insensitive but preserves original casing."""

    def test_mixed_case_sort(self):
        result = p.orq("SELECT Salary, name, Age FROM employees")
        assert result == "SELECT Age, name, Salary FROM employees"

    def test_upper_case(self):
        result = p.orq("SELECT SALARY, NAME, AGE FROM employees")
        assert result == "SELECT AGE, NAME, SALARY FROM employees"


class TestOrqWithExpressions:
    """Columns that contain function calls or parentheses."""

    def test_function_calls_preserved(self):
        sql = "SELECT COUNT(*), AVG(salary) FROM employees"
        result = p.orq(sql)
        assert "AVG(salary)" in result
        assert "COUNT(*)" in result

    def test_aliased_columns(self):
        result = p.orq("SELECT salary as s, name as n FROM employees")
        assert result == "SELECT name as n, salary as s FROM employees"


class TestOrqKeywordCasing:
    """SELECT and FROM keywords in different cases."""

    def test_lowercase_keywords(self):
        result = p.orq("select salary, name from employees")
        assert result == "select name, salary from employees"

    def test_mixed_keywords(self):
        result = p.orq("Select salary, name From employees")
        assert result == "Select name, salary From employees"


class TestOrqEdgeCases:
    """Non-SELECT queries and edge cases."""

    def test_non_select_unchanged(self):
        sql = "INSERT INTO employees (name) VALUES ('Alice')"
        assert p.orq(sql) == sql

    def test_empty_string(self):
        assert p.orq("") == ""

    def test_whitespace_handling(self):
        result = p.orq("SELECT  salary ,  name ,  age  FROM employees")
        assert "age" in result
        assert "name" in result
        assert "salary" in result
