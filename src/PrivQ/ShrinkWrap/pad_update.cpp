#include "shrinkwrap.h"

std::string shrinkwrap_pad_update(const std::string& sql) {
    const std::string target = "SET ";
    const std::string replacement = "SET pad_col = 0, /* shrinkwrap */ ";

    std::string result = sql;
    std::string::size_type pos = result.find(target);
    if (pos != std::string::npos) {
        result.replace(pos, target.size(), replacement);
    }
    return result;
}
