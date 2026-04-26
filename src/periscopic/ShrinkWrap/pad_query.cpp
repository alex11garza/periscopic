#include "shrinkwrap.h"

std::string shrinkwrap_pad_query(const std::string& sql) {
    return "\n    -- shrinkwrap padding\n    " + sql + "\n    -- end padding\n";
}
