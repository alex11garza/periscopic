#include "shrinkwrap.h"

std::string shrinkwrap_pad_delete(const std::string& sql) {
    const std::string target = "WHERE ";
    const std::string replacement = "WHERE 1=1 /* shrinkwrap */ AND ";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
