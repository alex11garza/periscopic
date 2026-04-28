#include "min_heap.h"

#include <algorithm>   // std::sort (used in snapshot)
#include <stdexcept>

namespace dp {

// ---------------------------------------------------------------------------
// push
// ---------------------------------------------------------------------------
void MinHeap::push(const TableEntry& entry) {
    data_.push_back(entry);
    bubble_up(data_.size() - 1);
}

// ---------------------------------------------------------------------------
// pop
// ---------------------------------------------------------------------------
TableEntry MinHeap::pop() {
    if (data_.empty()) {
        throw std::underflow_error("MinHeap::pop called on empty heap");
    }
    TableEntry top = data_[0];
    data_[0] = data_.back();
    data_.pop_back();
    if (!data_.empty()) {
        sift_down(0);
    }
    return top;
}

// ---------------------------------------------------------------------------
// peek
// ---------------------------------------------------------------------------
const TableEntry& MinHeap::peek() const {
    if (data_.empty()) {
        throw std::underflow_error("MinHeap::peek called on empty heap");
    }
    return data_[0];
}

// ---------------------------------------------------------------------------
// snapshot — sorted copy, heap unchanged
// ---------------------------------------------------------------------------
std::vector<TableEntry> MinHeap::snapshot() const {
    std::vector<TableEntry> copy = data_;
    std::sort(copy.begin(), copy.end(), [](const TableEntry& a, const TableEntry& b) {
        return a.noisy_size < b.noisy_size;
    });
    return copy;
}

// ---------------------------------------------------------------------------
// bubble_up
// ---------------------------------------------------------------------------
void MinHeap::bubble_up(size_t i) {
    while (i > 0) {
        const size_t p = parent(i);
        if (data_[p].noisy_size <= data_[i].noisy_size) break;
        std::swap(data_[i], data_[p]);
        i = p;
    }
}

// ---------------------------------------------------------------------------
// sift_down
// ---------------------------------------------------------------------------
void MinHeap::sift_down(size_t i) {
    const size_t n = data_.size();
    while (true) {
        size_t smallest = i;
        const size_t l  = left(i);
        const size_t r  = right(i);

        if (l < n && data_[l].noisy_size < data_[smallest].noisy_size) smallest = l;
        if (r < n && data_[r].noisy_size < data_[smallest].noisy_size) smallest = r;

        if (smallest == i) break;
        std::swap(data_[i], data_[smallest]);
        i = smallest;
    }
}

} // namespace dp
