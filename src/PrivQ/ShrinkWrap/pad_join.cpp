#include "shrinkwrap.h"

std::string shrinkwrap_pad_join(const std::string& sql) {
    return sql + " LEFT JOIN (SELECT 1 as dummy) sw ON 1=1 /* shrinkwrap join */";
}
