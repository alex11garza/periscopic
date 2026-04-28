#include "shrinkwrap.h"

std::string shrinkwrap_pad_orderby(const std::string& sql) {
    const std::string target = "ORDER BY ";
    const std::string replacement = "ORDER BY 0 /* shrinkwrap */, ";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
