/**
 * ORQ/bindings.cpp — pybind11 bindings for orq_sort_query.
 *
 * Exposes the C++ orq_sort_query() function to Python as:
 *   from periscopic._orq import sort_query
 */

#include <pybind11/pybind11.h>
#include "orq_sort_query.h"

namespace py = pybind11;

PYBIND11_MODULE(_orq, m) {
    m.doc() = R"(
        ORQ — Order-Respecting Query column sorter.

        Alphabetically sorts the SELECT column list of a SQL statement
        (case-insensitive) to improve AST parse-cache locality and reduce
        side-channel leakage from column ordering.
    )";

    m.def(
        "sort_query",
        &orq_sort_query,
        py::arg("sql"),
        R"(
        Sort the SELECT column list of a SQL query alphabetically.

        Args:
            sql (str): Input SQL string.

        Returns:
            str: SQL with SELECT columns sorted alphabetically.
                 Returns the original string unchanged if no SELECT list
                 is found (e.g. SELECT * or non-SELECT statements).

        Example:
            >>> sort_query("SELECT salary, name, age FROM employees")
            'SELECT age, name, salary FROM employees'
        )"
    );
}
