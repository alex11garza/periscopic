#include "laplace.h"

#include <algorithm>   // std::max
#include <cmath>       // std::log
#include <cstdint>
#include <random>
#include <stdexcept>

namespace dp {

// ---------------------------------------------------------------------------
// Internal RNG — seeded once per process via std::random_device
// ---------------------------------------------------------------------------
static std::mt19937_64& rng() {
    static std::mt19937_64 gen(std::random_device{}());
    return gen;
}

// ---------------------------------------------------------------------------
// laplace_sample
// ---------------------------------------------------------------------------
// Inverse-CDF of the half-Laplace (positive side only):
//   U ~ Uniform(0, 1)
//   |X| = -scale * ln(1 - U)
//
// We generate U in (0, 1) to avoid ln(0), then randomly flip sign before
// taking abs — this keeps the draw symmetric around 0 but we only expose |X|.
double laplace_sample(double scale) {
    if (scale <= 0.0) {
        throw std::invalid_argument("laplace_sample: scale must be > 0");
    }

    std::uniform_real_distribution<double> uniform(1e-10, 1.0);
    const double u    = uniform(rng());
    const double raw  = -scale * std::log(1.0 - u);   // positive half-Laplace

    // Randomly negate then re-abs — equivalent to drawing from the full
    // symmetric Laplace and then taking |X|.
    std::bernoulli_distribution coin(0.5);
    const double signed_raw = coin(rng()) ? raw : -raw;
    return std::abs(signed_raw);
}

// ---------------------------------------------------------------------------
// noisy_count
// ---------------------------------------------------------------------------
int64_t noisy_count(int64_t true_count, double epsilon, double sensitivity) {
    if (epsilon <= 0.0) {
        throw std::invalid_argument("noisy_count: epsilon must be > 0");
    }
    const double scale = sensitivity / epsilon;
    const double noisy = static_cast<double>(true_count) + laplace_sample(scale);
    // Clamp to non-negative and round to nearest integer
    return static_cast<int64_t>(std::max(0.0, std::round(noisy)));
}

} // namespace dp
