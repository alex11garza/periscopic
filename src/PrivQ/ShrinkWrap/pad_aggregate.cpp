#include "shrinkwrap.h"

std::string shrinkwrap_pad_aggregate(const std::string& sql) {
    const std::string target = "AVG(salary) as avg_salary";
    const std::string replacement = "AVG(salary) as avg_salary, /* shrinkwrap */ SUM(0) as pad_agg /* end */";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
