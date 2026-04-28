#pragma once
#include <string>

// Sorts the SELECT column list alphabetically (case-insensitive).
// Normalizes query structure to reduce side-channel leakage from column ordering.
// Heuristic: splits on commas not inside parentheses — works for simple SELECT lists.
std::string orq_sort_query(const std::string& sql);




//laplace distrubitoin and only use postive

//keep trakc of compute cost by checking the status of the Eplison of the privacy budget and the oppertunity cist of the records


