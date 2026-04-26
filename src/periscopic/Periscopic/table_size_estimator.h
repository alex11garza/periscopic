#pragma once

/**
 * table_size_estimator.h — Periscopic: differentially private table size map + join planner.
 *
 * The estimator holds a hash map of { table_name -> noisy_row_count } and a
 * min-heap over the same entries.  It does NOT touch the database — callers
 * feed raw catalog counts in and get a DP-noised, heap-ordered result back.
 * This keeps the DB layer out of the C++ PoC so the module can be tested
 * standalone with any source of row counts.
 *
 * Typical usage:
 *
 *   TableSizeEstimator est(0.5);           // epsilon = 0.5
 *   est.load({ {"users", 100},             // feed catalog counts
 *               {"orders", 200},
 *               {"products", 50} });
 *
 *   auto order = est.join_order({"orders", "users", "products"});
 *   // => ["products", "users", "orders"]  (smallest → largest, noisy)
 *
 *   auto snap  = est.heap_snapshot();      // inspect full heap for debugging
 */

#include "min_heap.h"

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace dp {

class TableSizeEstimator {
public:
    /**
     * @param epsilon  Privacy budget.  Smaller => more noise => more privacy.
     *                 Recommended range: 0.1 – 1.0.
     */
    explicit TableSizeEstimator(double epsilon = 0.5);

    /**
     * Load (or reload) raw catalog row-count estimates.
     * Applies Laplace noise to each count and rebuilds the heap.
     *
     * @param catalog  pairs of { table_name, true_row_count }
     */
    void load(const std::vector<std::pair<std::string, int64_t>>& catalog);

    /**
     * Look up the noisy estimate for a single table.
     * Returns -1 if the table is not in the map.
     */
    int64_t noisy_size(const std::string& table_name) const;

    /**
     * Given a list of table names, return them sorted smallest→largest
     * using noisy estimates.  Tables not in the map are sorted last.
     *
     * @param tables  unordered list of table names (e.g. from FROM/JOIN clause)
     * @return        same names, reordered
     */
    std::vector<std::string> join_order(const std::vector<std::string>& tables) const;

    /**
     * Return all entries from the heap sorted smallest→largest.
     * Non-destructive — heap is unchanged.
     */
    std::vector<TableEntry> heap_snapshot() const;

    /** Number of tables currently tracked. */
    size_t table_count() const { return size_map_.size(); }

    double epsilon() const { return epsilon_; }

private:
    double                                epsilon_;
    std::unordered_map<std::string, int64_t> size_map_;   // the hash map
    MinHeap                               heap_;
};

} // namespace dp
