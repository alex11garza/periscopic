#pragma once
#include <cstdint>
#include <string>

// Truncated Laplace mechanism from Bater et al. (Shrinkwrap, VLDB 2018, Def. 4).
// Samples integer noise from L(epsilon, delta, sensitivity) shifted by eta_0
// so that Pr[noise < sensitivity] <= delta, then clamps to max(noise, 0).
// Used by shrinkwrap_dp_resize to compute a DP-noisy LIMIT bound.
int64_t shrinkwrap_truncated_laplace(double epsilon, double delta, double sensitivity);

// Appends (or replaces) a LIMIT clause with `true_count + truncated_laplace(...)`,
// producing a SQL string whose result cardinality is differentially-private wrt
// the true_count. Implements the Resize step from Bater et al. Algorithm 1 at
// the SQL-text layer rather than over a secret-shared array.
std::string shrinkwrap_dp_resize(const std::string& sql,
                                 int64_t true_count,
                                 double epsilon,
                                 double delta,
                                 double sensitivity);


// Injects a dummy SUM(0) aggregate into the SELECT list after AVG(salary).
// Modifies the AST targetList — would execute on a real database.
std::string shrinkwrap_pad_aggregate(const std::string& sql);

// Replaces "SELECT *" with "SELECT *, 1 as pad_col" to inject a dummy column.
// Modifies the AST targetList — would execute on a real database.
std::string shrinkwrap_pad_column(const std::string& sql);

// Prepends a dummy CTE to a WITH clause.
// Modifies the AST withClause — would execute on a real database.
std::string shrinkwrap_pad_cte(const std::string& sql);

// Prepends "1=1 AND" to a DELETE WHERE clause.
// Modifies the AST whereClause — would execute on a real database.
std::string shrinkwrap_pad_delete(const std::string& sql);

// Injects a dummy column name into an INSERT statement's column list.
// Modifies the AST InsertStmt targetList — would execute on a real database.
std::string shrinkwrap_pad_insert(const std::string& sql);

// Appends a dummy LEFT JOIN subquery to the SQL statement.
// Modifies the AST fromClause — would execute on a real database.
std::string shrinkwrap_pad_join(const std::string& sql);

// Prepends a dummy "ORDER BY 0" to an existing ORDER BY clause.
// Modifies the AST sortClause — would execute on a real database.
std::string shrinkwrap_pad_orderby(const std::string& sql);

// Adds whitespace and SQL comments around the query.
// Note: SQL comments are stripped by the parser — no AST change occurs.
std::string shrinkwrap_pad_query(const std::string& sql);

// Injects a dummy column into an inner subquery SELECT list.
// Modifies the nested AST SelectStmt targetList — would execute on a real database.
std::string shrinkwrap_pad_subquery(const std::string& sql);

// Prepends a dummy "pad_col = 0" assignment to an UPDATE SET clause.
// Modifies the AST UpdateStmt targetList — would execute on a real database.
std::string shrinkwrap_pad_update(const std::string& sql);
