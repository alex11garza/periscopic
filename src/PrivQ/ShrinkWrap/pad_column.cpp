#include "shrinkwrap.h"

std::string shrinkwrap_pad_column(const std::string& sql) {
    const std::string target = "SELECT *";
    const std::string replacement = "SELECT *, /* shrinkwrap */ 1 as pad_col /* end */";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
