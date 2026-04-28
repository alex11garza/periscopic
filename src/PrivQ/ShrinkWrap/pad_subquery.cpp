#include "shrinkwrap.h"

std::string shrinkwrap_pad_subquery(const std::string& sql) {
    const std::string target = "SELECT AVG(price) FROM products";
    const std::string replacement = "SELECT AVG(price), /* shrinkwrap */ 0 as pad_col /* end */ FROM products";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
