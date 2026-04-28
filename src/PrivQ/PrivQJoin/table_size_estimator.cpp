#include "table_size_estimator.h"
#include "laplace.h"

#include <algorithm>   // std::sort, std::transform
#include <cctype>      // std::tolower
#include <stdexcept>
#include <string>

namespace dp {

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
static std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return s;
}

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------
TableSizeEstimator::TableSizeEstimator(double epsilon)
    : epsilon_(epsilon)
{
    if (epsilon <= 0.0) {
        throw std::invalid_argument("TableSizeEstimator: epsilon must be > 0");
    }
}

// ---------------------------------------------------------------------------
// load
// ---------------------------------------------------------------------------
void TableSizeEstimator::load(const std::vector<std::pair<std::string, int64_t>>& catalog) {
    size_map_.clear();
    heap_ = MinHeap{};

    for (const auto& entry : catalog) {
        const std::string key   = to_lower(entry.first);
        const int64_t     noisy = noisy_count(entry.second, epsilon_);

        size_map_[key] = noisy;
        heap_.push({ key, noisy });
    }
}

// ---------------------------------------------------------------------------
// noisy_size
// ---------------------------------------------------------------------------
int64_t TableSizeEstimator::noisy_size(const std::string& table_name) const {
    const auto it = size_map_.find(to_lower(table_name));
    return (it != size_map_.end()) ? it->second : -1;
}

// ---------------------------------------------------------------------------
// join_order
// ---------------------------------------------------------------------------
std::vector<std::string> TableSizeEstimator::join_order(
    const std::vector<std::string>& tables) const
{
    std::vector<std::string> sorted = tables;

    std::sort(sorted.begin(), sorted.end(),
        [this](const std::string& a, const std::string& b) {
            const int64_t sa = noisy_size(a);
            const int64_t sb = noisy_size(b);
            // Unknown tables (-1) sort last
            const int64_t wa = (sa < 0) ? INT64_MAX : sa;
            const int64_t wb = (sb < 0) ? INT64_MAX : sb;
            return wa < wb;
        });

    return sorted;
}

// ---------------------------------------------------------------------------
// heap_snapshot
// ---------------------------------------------------------------------------
std::vector<TableEntry> TableSizeEstimator::heap_snapshot() const {
    return heap_.snapshot();
}

} // namespace dp
