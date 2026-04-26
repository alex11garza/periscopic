/**
 * Periscopic/bindings.cpp — pybind11 bindings for the DP table size estimator.
 *
 * Exposes TableSizeEstimator and its helpers to Python as:
 *   from periscopic._periscopic import TableSizeEstimator, laplace_sample, noisy_count
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>       // auto-converts std::vector / std::pair
#include "table_size_estimator.h"
#include "laplace.h"

namespace py = pybind11;

PYBIND11_MODULE(_periscopic, m) {
    m.doc() = R"(
        Periscopic — Differentially private table size estimator.

        Adds Laplace(sensitivity/epsilon) noise to table row-count estimates
        from pg_class and stores them in a hash map + min-heap.  The heap
        drives smallest-first join ordering in the ORQ pipeline without ever
        storing or exposing true table sizes.
    )";

    // ── Free functions ───────────────────────────────────────────────────────

    m.def(
        "laplace_sample",
        &dp::laplace_sample,
        py::arg("scale"),
        R"(
        Draw one non-negative sample from Laplace(0, scale).

        Uses the inverse-CDF method then takes the absolute value so the
        result is always >= 0 (table sizes cannot be negative).

        Args:
            scale (float): b = sensitivity / epsilon.  Must be > 0.
        Returns:
            float: Non-negative Laplace sample.
        )"
    );

    m.def(
        "noisy_count",
        &dp::noisy_count,
        py::arg("true_count"),
        py::arg("epsilon"),
        py::arg("sensitivity") = 1.0,
        R"(
        Add Laplace noise to a true row count and return a non-negative integer.

        Satisfies epsilon-differential privacy for the given sensitivity.

        Args:
            true_count (int):    Raw row count (e.g. from pg_class.reltuples).
            epsilon (float):     Privacy budget.  Smaller => more noise.
            sensitivity (float): Query sensitivity, default 1 (one row).
        Returns:
            int: Noisy, non-negative row-count estimate.
        )"
    );

    // ── TableEntry (read-only data class) ───────────────────────────────────

    py::class_<dp::TableEntry>(m, "TableEntry")
        .def_readonly("table_name", &dp::TableEntry::table_name)
        .def_readonly("noisy_size", &dp::TableEntry::noisy_size)
        .def("__repr__", [](const dp::TableEntry& e) {
            return "TableEntry(table_name='" + e.table_name
                 + "', noisy_size=" + std::to_string(e.noisy_size) + ")";
        });

    // ── TableSizeEstimator ───────────────────────────────────────────────────

    py::class_<dp::TableSizeEstimator>(m, "TableSizeEstimator")
        .def(
            py::init<double>(),
            py::arg("epsilon") = 0.5,
            R"(
            Create a TableSizeEstimator.

            Args:
                epsilon (float): Privacy budget (default 0.5).
                                 Smaller => more Laplace noise => more privacy.
            )"
        )
        .def(
            "load",
            &dp::TableSizeEstimator::load,
            py::arg("catalog"),
            R"(
            Load raw catalog row-count estimates, apply Laplace noise, and
            rebuild the internal hash map and min-heap.

            Args:
                catalog (list[tuple[str, int]]): List of (table_name, true_row_count)
                                                 pairs, e.g. from pg_class.reltuples.
            Example:
                >>> est.load([("users", 100), ("orders", 200), ("products", 50)])
            )"
        )
        .def(
            "noisy_size",
            &dp::TableSizeEstimator::noisy_size,
            py::arg("table_name"),
            R"(
            Look up the noisy estimate for a single table.

            Args:
                table_name (str): Table name (case-insensitive).
            Returns:
                int: Noisy row count, or -1 if the table is not in the map.
            )"
        )
        .def(
            "join_order",
            &dp::TableSizeEstimator::join_order,
            py::arg("tables"),
            R"(
            Return the given table names sorted smallest-first using noisy estimates.
            Tables not in the map are sorted last.

            Args:
                tables (list[str]): Table names from a FROM/JOIN clause.
            Returns:
                list[str]: Same names reordered smallest → largest.

            Example:
                >>> est.join_order(["orders", "users", "products"])
                ['products', 'users', 'orders']
            )"
        )
        .def(
            "heap_snapshot",
            &dp::TableSizeEstimator::heap_snapshot,
            R"(
            Return all tracked tables sorted smallest → largest as TableEntry objects.
            Non-destructive — the internal heap is unchanged.

            Returns:
                list[TableEntry]: Sorted snapshot of the heap.
            )"
        )
        .def_property_readonly("table_count", &dp::TableSizeEstimator::table_count,
            "Number of tables currently tracked in the estimator.")
        .def_property_readonly("epsilon", &dp::TableSizeEstimator::epsilon,
            "Privacy budget this estimator was constructed with.");
}
