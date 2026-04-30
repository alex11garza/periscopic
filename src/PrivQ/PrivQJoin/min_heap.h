#pragma once

/**
 * min_heap.h — Min-heap keyed by noisy table size.
 *
 * Stores { table_name, noisy_size } entries so the ORQ join planner can
 * retrieve tables in smallest-first order in O(k log n) time.
 *
 * Standard binary min-heap backed by std::vector — no STL priority_queue
 * so we can expose a clean snapshot() without destroying the heap.
 */

#include <cstdint>
#include <string>
#include <vector>

namespace dp {

struct TableEntry {
    std::string table_name;
    int64_t     noisy_size;
};

class MinHeap {
public:
    MinHeap() = default;

    /** Insert an entry. O(log n). */
    void push(const TableEntry& entry);

    /** Remove and return the entry with the smallest noisy_size. O(log n). */
    TableEntry pop();

    /** Return the smallest entry without removing it. O(1). */
    const TableEntry& peek() const;

    /** Return all entries sorted smallest→largest without modifying the heap. */
    std::vector<TableEntry> snapshot() const;

    bool    empty() const { return data_.empty(); }
    size_t  size()  const { return data_.size(); }

private:
    std::vector<TableEntry> data_;

    void bubble_up(size_t i);
    void sift_down(size_t i);

    static size_t parent(size_t i) { return (i - 1) / 2; }
    static size_t left(size_t i)   { return 2 * i + 1; }
    static size_t right(size_t i)  { return 2 * i + 2; }
};

} // namespace dp
