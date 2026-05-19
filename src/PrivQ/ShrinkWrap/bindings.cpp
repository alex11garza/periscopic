/**
 * ShrinkWrap/bindings.cpp — pybind11 bindings for all shrinkwrap pad functions.
 *
 * Exposes each C++ pad function to Python as:
 *   from PrivQ._shrinkwrap import pad_query, pad_column, ...
 */

#include <pybind11/pybind11.h>
#include "shrinkwrap.h"

namespace py = pybind11;

PYBIND11_MODULE(_shrinkwrap, m) {
    m.doc() = R"(
        ShrinkWrap — SQL structural padding.

        Wraps SQL statements with dummy clauses so an observer watching
        query traffic cannot infer the true query shape from its syntax.
        Each function targets a different AST node type.
    )";

    m.def(
        "pad_query",
        &shrinkwrap_pad_query,
        py::arg("sql"),
        R"(
        Wrap the query with whitespace and SQL comment padding.
        Targets: outer query shell. No AST change — comments are stripped by the parser.

        Args:
            sql (str): Input SQL string.
        Returns:
            str: SQL wrapped with padding comments.
        )"
    );

    m.def(
        "pad_column",
        &shrinkwrap_pad_column,
        py::arg("sql"),
        R"(
        Inject a dummy constant column into a SELECT * statement.
        Targets: AST targetList.

        Args:
            sql (str): Input SQL string containing SELECT *.
        Returns:
            str: SQL with a dummy column appended to the SELECT list.
        )"
    );

    m.def(
        "pad_aggregate",
        &shrinkwrap_pad_aggregate,
        py::arg("sql"),
        R"(
        Inject a dummy SUM(0) aggregate after an AVG() expression.
        Targets: AST targetList aggregate nodes.

        Args:
            sql (str): Input SQL string containing AVG(...).
        Returns:
            str: SQL with a dummy aggregate appended.
        )"
    );

    m.def(
        "pad_cte",
        &shrinkwrap_pad_cte,
        py::arg("sql"),
        R"(
        Prepend a dummy CTE to a WITH clause.
        Targets: AST withClause.

        Args:
            sql (str): Input SQL string containing a WITH clause.
        Returns:
            str: SQL with a dummy CTE prepended.
        )"
    );

    m.def(
        "pad_join",
        &shrinkwrap_pad_join,
        py::arg("sql"),
        R"(
        Append a dummy LEFT JOIN subquery to the FROM clause.
        Targets: AST fromClause.

        Args:
            sql (str): Input SQL string.
        Returns:
            str: SQL with a dummy LEFT JOIN appended.
        )"
    );

    m.def(
        "pad_orderby",
        &shrinkwrap_pad_orderby,
        py::arg("sql"),
        R"(
        Prepend a dummy ORDER BY 0 to an existing ORDER BY clause.
        Targets: AST sortClause.

        Args:
            sql (str): Input SQL string containing ORDER BY.
        Returns:
            str: SQL with ORDER BY 0 prepended.
        )"
    );

    m.def(
        "pad_subquery",
        &shrinkwrap_pad_subquery,
        py::arg("sql"),
        R"(
        Inject a dummy column into an inner subquery SELECT list.
        Targets: nested AST SelectStmt targetList.

        Args:
            sql (str): Input SQL string containing a subquery.
        Returns:
            str: SQL with a dummy column in the subquery.
        )"
    );

    m.def(
        "pad_insert",
        &shrinkwrap_pad_insert,
        py::arg("sql"),
        R"(
        Inject a dummy column name into an INSERT statement's column list.
        Targets: AST InsertStmt targetList.

        Args:
            sql (str): Input SQL INSERT string.
        Returns:
            str: INSERT with a dummy column appended.
        )"
    );

    m.def(
        "pad_update",
        &shrinkwrap_pad_update,
        py::arg("sql"),
        R"(
        Prepend a dummy assignment to an UPDATE SET clause.
        Targets: AST UpdateStmt targetList.

        Args:
            sql (str): Input SQL UPDATE string.
        Returns:
            str: UPDATE with a dummy SET assignment prepended.
        )"
    );

    m.def(
        "pad_delete",
        &shrinkwrap_pad_delete,
        py::arg("sql"),
        R"(
        Prepend "1=1 AND" to a DELETE WHERE clause.
        Targets: AST whereClause.

        Args:
            sql (str): Input SQL DELETE string.
        Returns:
            str: DELETE with a dummy WHERE condition prepended.
        )"
    );

    m.def(
        "truncated_laplace",
        &shrinkwrap_truncated_laplace,
        py::arg("epsilon"),
        py::arg("delta"),
        py::arg("sensitivity") = 1.0,
        R"(
        Sample integer noise from the truncated Laplace mechanism of
        Bater et al. (Shrinkwrap, VLDB 2018, Def. 4).

        Returns a non-negative integer eta such that Pr[eta < sensitivity] <= delta,
        drawn from a Laplace(scale=sensitivity/epsilon) centered at the shift eta_0
        prescribed by the paper, then clamped to max(eta, 0).

        Args:
            epsilon     (float): Privacy budget for this release. Must be > 0.
            delta       (float): Failure probability. Must be in (0, 1).
            sensitivity (float): Query sensitivity Delta_c. Default 1.0 (counting query).
        Returns:
            int: Non-negative integer noise sample.
        )"
    );

    m.def(
        "dp_resize",
        &shrinkwrap_dp_resize,
        py::arg("sql"),
        py::arg("true_count"),
        py::arg("epsilon"),
        py::arg("delta"),
        py::arg("sensitivity") = 1.0,
        R"(
        Rewrite a SQL query so its result size is bounded by a differentially-
        private LIMIT, implementing the Resize step from Bater et al. Algorithm 1
        at the SQL-text layer.

        Computes c_tilde = true_count + truncated_laplace(epsilon, delta, sensitivity)
        and appends `LIMIT c_tilde`. If the query already ends with a LIMIT, it is
        replaced; trailing semicolons are preserved.

        Args:
            sql         (str):   Input SQL string.
            true_count  (int):   True (non-private) result cardinality. Must be >= 0.
            epsilon     (float): Privacy budget. Must be > 0.
            delta       (float): Failure probability. Must be in (0, 1).
            sensitivity (float): Sensitivity Delta_c of the cardinality query. Default 1.0.
        Returns:
            str: SQL string with a DP-noised LIMIT clause.
        )"
    );
}
