// ShrinkWrap/dp_resize.cpp — Truncated Laplace mechanism and SQL LIMIT rewrite.
//
// Implements the Resize() step from Bater et al., "Shrinkwrap: Efficient SQL
// Query Processing in Differentially Private Data Federations" (VLDB 2018),
// adapted to operate at the SQL-text layer:
//
//   c_tilde = true_count + max(eta, 0)
//   eta ~ L(epsilon, delta, sensitivity)        (Bater Def. 4)
//
// The DP guarantee (epsilon, delta) applies to releases of the size-bound
// LIMIT value, treating the input as a count query on a neighboring database.

#include "shrinkwrap.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <random>
#include <regex>
#include <stdexcept>
#include <string>

namespace {

std::mt19937_64& rng() {
    static std::mt19937_64 gen(std::random_device{}());
    return gen;
}

// Draw from a standard Laplace(mu=0, scale=b) via inverse CDF.
double laplace_draw(double scale) {
    std::uniform_real_distribution<double> uniform(-0.5 + 1e-12, 0.5 - 1e-12);
    const double u = uniform(rng());
    // Equivalent to: mu + b * sign(u') * ln(1 - 2|u'|) for u' = u + 0.5,
    // collapsed to a single signed expression.
    return -scale * std::copysign(std::log(1.0 - 2.0 * std::abs(u)), u);
}

}  // namespace

// ---------------------------------------------------------------------------
// Truncated Laplace mechanism — Bater et al. Def. 4
// ---------------------------------------------------------------------------
//
// PDF (over the reals):
//     p * exp(-(epsilon / Delta_c) * |x - eta_0|)
// where
//     p     = (e^(eps/Dc) - 1) / (e^(eps/Dc) + 1)
//     eta_0 = -(Dc * ln((e^(eps/Dc) + 1) * delta) / eps) + Dc
//
// This is a Laplace(mu=eta_0, scale=Delta_c/epsilon) distribution; the paper
// truncates the realization at zero (max(eta, 0)) before adding to the count.
// The shift eta_0 is chosen so Pr[eta < Delta_c] <= delta, guaranteeing that
// the noisy bound almost certainly exceeds the true count.
int64_t shrinkwrap_truncated_laplace(double epsilon,
                                     double delta,
                                     double sensitivity) {
    if (epsilon <= 0.0) {
        throw std::invalid_argument("truncated_laplace: epsilon must be > 0");
    }
    if (delta <= 0.0 || delta >= 1.0) {
        throw std::invalid_argument("truncated_laplace: delta must be in (0, 1)");
    }
    if (sensitivity <= 0.0) {
        throw std::invalid_argument("truncated_laplace: sensitivity must be > 0");
    }

    const double r       = epsilon / sensitivity;
    const double exp_r   = std::exp(r);
    const double eta_0   = -(sensitivity * std::log((exp_r + 1.0) * delta) / epsilon) + sensitivity;
    const double scale   = sensitivity / epsilon;
    const double sample  = eta_0 + laplace_draw(scale);
    const double clamped = std::max(0.0, sample);
    return static_cast<int64_t>(std::round(clamped));
}

// ---------------------------------------------------------------------------
// SQL LIMIT rewrite — DP Resize at the text layer
// ---------------------------------------------------------------------------
//
// Computes c_tilde = true_count + truncated_laplace(eps, delta, sens) and
// rewrites the SQL so its result size is bounded by c_tilde. If the query
// already has a trailing LIMIT, it is replaced; otherwise LIMIT is appended.
//
// Only the trailing LIMIT (the one bounding the outermost SELECT's result)
// is touched. LIMITs inside subqueries are left alone — they belong to a
// different operator and have their own sensitivities.
std::string shrinkwrap_dp_resize(const std::string& sql,
                                 int64_t true_count,
                                 double epsilon,
                                 double delta,
                                 double sensitivity) {
    if (true_count < 0) {
        throw std::invalid_argument("dp_resize: true_count must be >= 0");
    }

    const int64_t noise   = shrinkwrap_truncated_laplace(epsilon, delta, sensitivity);
    const int64_t c_tilde = true_count + noise;

    // Strip a single trailing semicolon (and the whitespace before it) so we
    // can append cleanly, remembering whether one was there to re-add.
    std::string body = sql;
    bool had_semi    = false;
    {
        auto rit = body.rbegin();
        while (rit != body.rend() && std::isspace(static_cast<unsigned char>(*rit))) ++rit;
        if (rit != body.rend() && *rit == ';') {
            had_semi = true;
            body.erase(body.size() - 1 - std::distance(body.rbegin(), rit));
            // trim trailing whitespace after erase
            while (!body.empty() && std::isspace(static_cast<unsigned char>(body.back()))) {
                body.pop_back();
            }
        }
    }

    // Match a trailing `LIMIT <number>` (case-insensitive, optional whitespace).
    // We only replace it if it's the last token of the (semicolon-stripped) body.
    static const std::regex trailing_limit(
        R"((.*?)\s+[Ll][Ii][Mm][Ii][Tt]\s+\d+\s*$)",
        std::regex::ECMAScript
    );

    std::smatch m;
    std::string rewritten;
    if (std::regex_match(body, m, trailing_limit)) {
        rewritten = m[1].str() + " LIMIT " + std::to_string(c_tilde);
    } else {
        rewritten = body + " LIMIT " + std::to_string(c_tilde);
    }

    if (had_semi) rewritten += ";";
    return rewritten;
}
