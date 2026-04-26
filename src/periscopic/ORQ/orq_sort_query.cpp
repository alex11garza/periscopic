#include "orq_sort_query.h"

#include <algorithm>
#include <cctype>
#include <regex>
#include <sstream>
#include <vector>

// Splits a SELECT list on commas that are not inside parentheses.
static std::vector<std::string> split_select_list(const std::string& s) {
    std::vector<std::string> parts;
    int depth = 0;
    std::string current;
    for (char c : s) {
        if (c == '(') ++depth;
        else if (c == ')') --depth;

        if (c == ',' && depth == 0) {
            parts.push_back(current);
            current.clear();
        } else {
            current += c;
        }
    }
    if (!current.empty()) {
        parts.push_back(current);
    }
    return parts;
}

// Trims leading and trailing whitespace.
static std::string trim(const std::string& s) {
    const auto start = s.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    const auto end = s.find_last_not_of(" \t\n\r");
    return s.substr(start, end - start + 1);
}

std::string orq_sort_query(const std::string& sql) {
    // Match the SELECT list between SELECT ... FROM (case-insensitive).
    // Note: (?i) inline flag is not supported by std::regex on macOS libc++;
    // pass std::regex::icase as a flag instead.
    std::regex select_re(
        R"((SELECT\s+)(.*?)(\s+FROM\s))",
        std::regex::icase
    );

    std::smatch m;
    if (!std::regex_search(sql, m, select_re)) {
        return sql;
    }

    const std::string prefix     = sql.substr(0, m.position(2));
    const std::string select_list = m[2].str();
    const std::string suffix     = sql.substr(m.position(2) + m.length(2));

    std::vector<std::string> parts = split_select_list(select_list);
    for (auto& p : parts) {
        p = trim(p);
    }

    std::sort(parts.begin(), parts.end(), [](const std::string& a, const std::string& b) {
        std::string la = a, lb = b;
        std::transform(la.begin(), la.end(), la.begin(), ::tolower);
        std::transform(lb.begin(), lb.end(), lb.begin(), ::tolower);
        return la < lb;
    });

    std::string sorted_list;
    for (std::size_t i = 0; i < parts.size(); ++i) {
        if (i > 0) sorted_list += ", ";
        sorted_list += parts[i];
    }

    return prefix + sorted_list + suffix;
}





