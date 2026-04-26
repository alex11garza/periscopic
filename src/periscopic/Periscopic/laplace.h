#pragma once

/**
 * laplace.h — Laplace mechanism for differential privacy.
 *
 * Provides epsilon-DP noise for table row-count estimates.
 * Only the positive half of the distribution is used (counts can't be negative).
 *
 * Privacy guarantee:
 *   Adding Laplace(sensitivity / epsilon) noise to a count achieves
 *   epsilon-differential privacy for sensitivity=1 (one row).
 */

#include <cstdint>

namespace dp {

/**
 * Draw one sample from Laplace(0, scale) using the inverse-CDF method,
 * then take the absolute value so the result is non-negative.
 *
 * @param scale  b = sensitivity / epsilon  (must be > 0)
 * @return       non-negative sample
 */
double laplace_sample(double scale);

/**
 * Add Laplace noise to a true row count and return a non-negative integer.
 *
 * @param true_count  pg_class.reltuples or similar catalog estimate
 * @param epsilon     privacy budget  (smaller => more noise => more privacy)
 * @param sensitivity query sensitivity, default 1 (one row)
 * @return            noisy, non-negative row-count estimate
 */
int64_t noisy_count(int64_t true_count, double epsilon, double sensitivity = 1.0);

} // namespace dp
