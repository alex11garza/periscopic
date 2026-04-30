#include "shrinkwrap.h"

std::string shrinkwrap_pad_cte(const std::string& sql) {
    const std::string target = "WITH ";
    const std::string replacement = "WITH dummy_cte AS (SELECT 1 as pad_col), /* shrinkwrap */ ";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
