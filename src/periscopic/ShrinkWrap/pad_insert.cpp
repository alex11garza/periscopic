#include "shrinkwrap.h"

std::string shrinkwrap_pad_insert(const std::string& sql) {
    const std::string target = ") VALUES (";
    const std::string replacement = ", pad_col /* shrinkwrap */) VALUES (";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
