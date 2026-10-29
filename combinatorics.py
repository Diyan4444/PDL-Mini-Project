# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: combinatorics.py - Core mathematical counting algorithms, identities, and listing

import math
import itertools


def factorial(n):
    """Computes n! = n * (n - 1) * ... * 1 using an iterative loop.
    
    0! is defined as 1.
    Negative numbers are rejected.
    The result is cross-checked against math.factorial.
    """
    if not isinstance(n, int):
        raise TypeError("Factorial argument must be an integer.")
    if n < 0:
        raise ValueError("Factorial is only defined for non-negative integers.")
    
    result = 1
    for i in range(1, n + 1):
        result = result * i
    
    # Cross-check with standard math library
    check = math.factorial(n)
    if result != check:
        raise RuntimeError("Internal math cross-check failed for factorial(" + str(n) + ")")
    
    return result


def permutations(n, r):
    """Computes P(n, r) = n! / (n - r)! using exact integer arithmetic.
    
    Requires integers n >= 0 and 0 <= r <= n.
    Order matters in permutations.
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0:
        raise ValueError("n must be non-negative (n >= 0).")
    if r < 0:
        raise ValueError("r must be non-negative (r >= 0).")
    if r > n:
        raise ValueError("r cannot be greater than n (r <= n required).")
    
    numerator = factorial(n)
    denominator = factorial(n - r)
    result = numerator // denominator
    
    # Cross-check with math.perm
    check = math.perm(n, r)
    if result != check:
        raise RuntimeError("Internal math cross-check failed for permutations(" + str(n) + ", " + str(r) + ")")
    
    return result


def combinations(n, r):
    """Computes C(n, r) = n! / (r! * (n - r)!) using exact integer division.
    
    Requires integers n >= 0 and 0 <= r <= n.
    Order does not matter in combinations.
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0:
        raise ValueError("n must be non-negative (n >= 0).")
    if r < 0:
        raise ValueError("r must be non-negative (r >= 0).")
    if r > n:
        raise ValueError("r cannot be greater than n (r <= n required).")
    
    numerator = factorial(n)
    denominator = factorial(r) * factorial(n - r)
    result = numerator // denominator
    
    # Cross-check with math.comb
    check = math.comb(n, r)
    if result != check:
        raise RuntimeError("Internal math cross-check failed for combinations(" + str(n) + ", " + str(r) + ")")
    
    return result


def permutations_with_repetition(n, r):
    """Computes permutations with replacement: n^r.
    
    Each of the r positions can be chosen independently from n choices.
    Requires n >= 0 and r >= 0. Note that r > n is permissible.
    Convention 0^0 = 1 (the single empty sequence).
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0:
        raise ValueError("n and r must be non-negative.")
    
    if n == 0 and r == 0:
        return 1
    if n == 0 and r > 0:
        return 0
    
    return n ** r


def combinations_with_repetition(n, r):
    """Computes combinations with replacement (multichoose): C(n + r - 1, r).
    
    Also known as stars-and-bars distribution of r identical items into n distinct bins.
    For n = 0: returns 1 if r = 0, otherwise 0.
    For r = 0: returns 1 for any n >= 0.
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0:
        raise ValueError("n and r must be non-negative.")
    
    if n == 0:
        if r == 0:
            return 1
        return 0
    if r == 0:
        return 1
    
    return combinations(n + r - 1, r)


def multiset_arrangements_count(text):
    """Computes the number of distinct permutations of a multiset string.
    
    Formula: n! / (n1! * n2! * ... * nk!)
    Frequencies of characters are stored in a dictionary.
    Returns a tuple: (total_arrangements, frequency_dictionary).
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")
    
    length = len(text)
    if length == 0:
        return (1, {})
    
    # Count frequencies using a dictionary
    freq = {}
    for ch in text:
        if ch in freq:
            freq[ch] = freq[ch] + 1
        else:
            freq[ch] = 1
    
    numerator = factorial(length)
    denominator = 1
    for char_key in freq:
        count = freq[char_key]
        denominator = denominator * factorial(count)
    
    total = numerator // denominator
    return (total, freq)


def verify_binomial_identities(n, r):
    """Verifies core binomial coefficient identities for chosen n and r.
    
    1. Symmetry: C(n, r) = C(n, n - r)
    2. Pascal's Identity: C(n, r) = C(n - 1, r - 1) + C(n - 1, r)
       (Valid when n >= 1 and 1 <= r <= n - 1)
    3. Row Sum Identity: Sum_{k=0}^{n} C(n, k) = 2^n
    
    Returns a dictionary of verification reports.
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n:
        raise ValueError("Requires 0 <= r <= n.")
    
    c_nr = combinations(n, r)
    
    # 1. Symmetry check
    c_sym = combinations(n, n - r)
    sym_verified = (c_nr == c_sym)
    
    # 2. Pascal's identity check
    if n >= 1 and 1 <= r <= (n - 1):
        pascal_sum = combinations(n - 1, r - 1) + combinations(n - 1, r)
        pascal_verified = (c_nr == pascal_sum)
        pascal_applicable = True
        pascal_note = "C(" + str(n-1) + "," + str(r-1) + ") + C(" + str(n-1) + "," + str(r) + ") = " + str(pascal_sum)
    else:
        pascal_verified = None
        pascal_applicable = False
        pascal_note = "Pascal's identity applies to interior elements where n >= 1 and 1 <= r <= n - 1."
    
    # 3. Row sum check
    computed_row_sum = 0
    for k in range(n + 1):
        computed_row_sum = computed_row_sum + combinations(n, k)
    theoretical_pow2 = 2 ** n
    row_sum_verified = (computed_row_sum == theoretical_pow2)
    
    report = {
        "n": n,
        "r": r,
        "c_nr": c_nr,
        "symmetry_verified": sym_verified,
        "c_sym": c_sym,
        "pascal_applicable": pascal_applicable,
        "pascal_verified": pascal_verified,
        "pascal_note": pascal_note,
        "row_sum_verified": row_sum_verified,
        "row_sum_value": computed_row_sum,
        "power_of_two": theoretical_pow2
    }
    return report


def generate_pascal_triangle(num_rows):
    """Generates Pascal's triangle from row 0 to row (num_rows - 1).
    
    Each row is constructed iteratively from the preceding row:
    row[j] = prev_row[j - 1] + prev_row[j].
    Every generated element is cross-verified against combinations(row_idx, col_idx).
    """
    if not isinstance(num_rows, int):
        raise TypeError("Number of rows must be an integer.")
    if num_rows < 1 or num_rows > 15:
        raise ValueError("Number of rows must be between 1 and 15.")
    
    triangle = []
    for i in range(num_rows):
        if i == 0:
            current_row = [1]
        else:
            prev_row = triangle[i - 1]
            current_row = [1]
            for j in range(1, i):
                current_row.append(prev_row[j - 1] + prev_row[j])
            current_row.append(1)
        
        # Verify every entry against combinations formula C(i, j)
        for col_idx in range(len(current_row)):
            expected = combinations(i, col_idx)
            if current_row[col_idx] != expected:
                raise RuntimeError("Pascal entry mismatch at row " + str(i) + ", col " + str(col_idx))
        
        triangle.append(current_row)
    
    return triangle


def binomial_expansion_terms(n, a, b):
    """Computes terms of (a*x + b*y)^n using binomial theorem.
    
    Formula: (a*x + b*y)^n = Sum_{k=0}^{n} C(n, k) * (a*x)^(n - k) * (b*y)^k
    Each term is represented as a tuple: (coefficient, x_power, y_power).
    """
    if not isinstance(n, int) or not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("n, a, and b must be integers.")
    if n < 0 or n > 20:
        raise ValueError("Exponent n must be between 0 and 20.")
    if abs(a) > 10 or abs(b) > 10:
        raise ValueError("Coefficients a and b must have absolute value <= 10.")
    
    terms = []
    for k in range(n + 1):
        comb_val = combinations(n, k)
        a_factor = a ** (n - k)
        b_factor = b ** k
        coeff = comb_val * a_factor * b_factor
        x_power = n - k
        y_power = k
        terms.append((coeff, x_power, y_power))
    
    return terms


def format_single_term(coeff, x_pow, y_pow, is_first):
    """Formats one term of a polynomial expansion into plain ASCII text."""
    if coeff == 0:
        return ""
    
    sign_str = ""
    abs_coeff = abs(coeff)
    
    if is_first:
        if coeff < 0:
            sign_str = "-"
    else:
        if coeff < 0:
            sign_str = " - "
        else:
            sign_str = " + "
    
    var_parts = []
    if x_pow > 0:
        if x_pow == 1:
            var_parts.append("x")
        else:
            var_parts.append("x^" + str(x_pow))
    
    if y_pow > 0:
        if y_pow == 1:
            var_parts.append("y")
        else:
            var_parts.append("y^" + str(y_pow))
    
    var_str = "*".join(var_parts)
    
    if len(var_parts) == 0:
        term_text = str(abs_coeff)
    else:
        if abs_coeff == 1:
            term_text = var_str
        else:
            term_text = str(abs_coeff) + "*" + var_str
    
    return sign_str + term_text


def format_binomial_expansion(terms):
    """Formats a list of (coeff, x_pow, y_pow) tuples into a full ASCII polynomial."""
    if not terms:
        return "0"
    
    rendered_parts = []
    is_first = True
    for coeff, x_pow, y_pow in terms:
        if coeff == 0:
            continue
        rendered_term = format_single_term(coeff, x_pow, y_pow, is_first)
        if rendered_term != "":
            rendered_parts.append(rendered_term)
            is_first = False
    
    if len(rendered_parts) == 0:
        return "0"
    
    return "".join(rendered_parts)


def list_letter_permutations(n, r):
    """Lists permutations of the first n uppercase letters taken r at a time.
    
    Arrangements are stored as tuples.
    A set of tuples is used to verify uniqueness.
    Returns (list_of_tuples, theoretical_count, is_match).
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n or n > 8:
        raise ValueError("n must be between 0 and 8, and 0 <= r <= n.")
    
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    items = list(alphabet[:n])
    
    raw_perms = itertools.permutations(items, r)
    tuple_list = []
    unique_set = set()
    
    for p in raw_perms:
        tup = tuple(p)
        tuple_list.append(tup)
        unique_set.add(tup)
    
    theoretical = permutations(n, r)
    is_match = (len(tuple_list) == theoretical) and (len(unique_set) == theoretical)
    
    return (tuple_list, theoretical, is_match)


def list_letter_combinations(n, r):
    """Lists combinations of the first n uppercase letters taken r at a time.
    
    Groups are stored as tuples.
    A set of tuples is used to verify uniqueness.
    Returns (list_of_tuples, theoretical_count, is_match).
    """
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n or n > 8:
        raise ValueError("n must be between 0 and 8, and 0 <= r <= n.")
    
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    items = list(alphabet[:n])
    
    raw_combs = itertools.combinations(items, r)
    tuple_list = []
    unique_set = set()
    
    for c in raw_combs:
        tup = tuple(c)
        tuple_list.append(tup)
        unique_set.add(tup)
    
    theoretical = combinations(n, r)
    is_match = (len(tuple_list) == theoretical) and (len(unique_set) == theoretical)
    
    return (tuple_list, theoretical, is_match)


def list_multiset_permutations(text):
    """Lists all distinct permutations of a multiset string.
    
    Uses itertools.permutations, stores arrangements as tuples,
    and inserts them into a set to eliminate duplicate permutations.
    Returns (distinct_list, theoretical_count, is_match).
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")
    if len(text) > 8:
        raise ValueError("Listing is capped at 8 characters for performance.")
    
    items = list(text)
    raw_perms = itertools.permutations(items)
    
    unique_set = set()
    for p in raw_perms:
        unique_set.add(tuple(p))
    
    distinct_list = sorted(list(unique_set))
    theoretical, _ = multiset_arrangements_count(text)
    is_match = (len(distinct_list) == theoretical)
    
    return (distinct_list, theoretical, is_match)
