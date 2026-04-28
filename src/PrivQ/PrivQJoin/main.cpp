/**
 * main.cpp — standalone driver for the PrivQ join reorder stage
 *
 * Simulates feeding catalog row counts (as you would from pg_class.reltuples)
 * into the estimator and exercising each function individually:
 *
 *   1. laplace_sample / noisy_count  — show raw noise draws
 *   2. MinHeap push/pop/peek/snapshot
 *   3. TableSizeEstimator::load + join_order + heap_snapshot
 *
 * Build:
 *   cd src/PrivQ/PrivQJoin && make
 * Run:
 *   ./privq_join
 */

#include "laplace.h"
#include "min_heap.h"
#include "table_size_estimator.h"

#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
static void section(const std::string& title) {
    std::cout << "\n" << std::string(60, '=') << "\n"
              << "  " << title << "\n"
              << std::string(60, '=') << "\n";
}

// ---------------------------------------------------------------------------
// 1. Laplace noise demo
// ---------------------------------------------------------------------------
static void demo_laplace() {
    section("1. Laplace Noise  (laplace_sample / noisy_count)");

    const double epsilon     = 0.5;
    const double sensitivity = 1.0;
    const double scale       = sensitivity / epsilon;

    std::cout << "  epsilon=" << epsilon
              << "  sensitivity=" << sensitivity
              << "  scale=" << scale << "\n\n";

    std::cout << "  10 raw laplace_sample(" << scale << ") draws:\n  ";
    for (int i = 0; i < 10; ++i) {
        std::cout << std::fixed << std::setprecision(2)
                  << dp::laplace_sample(scale) << "  ";
    }
    std::cout << "\n\n";

    // Simulate noising a pg_class.reltuples value
    const int64_t true_rows = 100;
    std::cout << "  noisy_count for true_count=" << true_rows
              << " over 5 draws:\n";
    for (int i = 0; i < 5; ++i) {
        std::cout << "    draw " << (i + 1) << " => "
                  << dp::noisy_count(true_rows, epsilon) << " rows\n";
    }
}

// ---------------------------------------------------------------------------
// 2. MinHeap demo
// ---------------------------------------------------------------------------
static void demo_heap() {
    section("2. MinHeap  (push / pop / peek / snapshot)");

    dp::MinHeap heap;
    const std::vector<dp::TableEntry> entries = {
        { "orders",   200 },
        { "users",    100 },
        { "products",  50 },
        { "sessions", 150 },
        { "employees", 80 },
    };

    std::cout << "  Pushing entries:\n";
    for (const auto& e : entries) {
        std::cout << "    push  " << std::setw(12) << e.table_name
                  << "  size=" << e.noisy_size << "\n";
        heap.push(e);
    }

    std::cout << "\n  peek (min) => "
              << heap.peek().table_name << "  size=" << heap.peek().noisy_size << "\n";

    std::cout << "\n  snapshot (sorted, heap unchanged):\n";
    for (const auto& e : heap.snapshot()) {
        std::cout << "    " << std::setw(12) << e.table_name
                  << "  ~" << e.noisy_size << " rows\n";
    }

    std::cout << "\n  pop sequence:\n";
    while (!heap.empty()) {
        const auto e = heap.pop();
        std::cout << "    pop => " << std::setw(12) << e.table_name
                  << "  size=" << e.noisy_size << "\n";
    }
}

// ---------------------------------------------------------------------------
// 3. TableSizeEstimator demo
// ---------------------------------------------------------------------------
static void demo_estimator() {
    section("3. TableSizeEstimator  (load / join_order / heap_snapshot)");

    // Simulated pg_class.reltuples values
    const std::vector<std::pair<std::string, int64_t>> catalog = {
        { "users",     100 },
        { "employees",  80 },
        { "customers",  50 },
        { "orders",    200 },
        { "products",   50 },
        { "sessions",  100 },
    };

    dp::TableSizeEstimator est(0.5);  // epsilon = 0.5
    est.load(catalog);

    std::cout << "  Loaded " << est.table_count()
              << " tables (epsilon=" << est.epsilon() << ")\n\n";

    std::cout << "  Noisy size map (hash map):\n";
    for (const auto& row : catalog) {
        std::cout << "    " << std::setw(12) << row.first
                  << "  true=" << std::setw(4) << row.second
                  << "  noisy=" << est.noisy_size(row.first) << "\n";
    }

    std::cout << "\n  Heap snapshot (smallest → largest):\n";
    for (const auto& e : est.heap_snapshot()) {
        std::cout << "    " << std::setw(12) << e.table_name
                  << "  ~" << e.noisy_size << " rows\n";
    }

    // join_order examples
    const std::vector<std::vector<std::string>> queries = {
        { "orders", "users", "products" },
        { "sessions", "employees", "customers", "orders" },
        { "users" },
    };

    std::cout << "\n  join_order examples:\n";
    for (const auto& q : queries) {
        std::cout << "    input:  [";
        for (size_t i = 0; i < q.size(); ++i) {
            if (i) std::cout << ", ";
            std::cout << q[i];
        }
        std::cout << "]\n    output: [";
        const auto ordered = est.join_order(q);
        for (size_t i = 0; i < ordered.size(); ++i) {
            if (i) std::cout << " → ";
            std::cout << ordered[i];
        }
        std::cout << "]\n\n";
    }

    // Unknown table falls to the end
    std::cout << "  Unknown table sorts last:\n";
    const auto with_unknown = est.join_order({ "orders", "unknown_table", "products" });
    std::cout << "    [";
    for (size_t i = 0; i < with_unknown.size(); ++i) {
        if (i) std::cout << " → ";
        std::cout << with_unknown[i];
    }
    std::cout << "]\n";
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------
int main() {
    std::cout << "\n╔══════════════════════════════════════════════════════════╗\n"
              << "║   PrivQ Join Reorder Standalone Demo                     ║\n"
              << "╚══════════════════════════════════════════════════════════╝\n";

    demo_laplace();
    demo_heap();
    demo_estimator();

    std::cout << "\n";
    return 0;
}
