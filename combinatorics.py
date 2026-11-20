# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Core counting functions used by the CLI, the web server and the charts.
# Python integers have unlimited size, so every result here is exact (no rounding),
# even for inputs like 1000! that have thousands of digits.

import math
import itertools
from collections import Counter
from fractions import Fraction

LETTERS = "ABCDEFGH"


def check_int(*values):
    # bool is a subclass of int in Python (True == 1), so it has to be rejected explicitly.
    for v in values:
        if not isinstance(v, int) or isinstance(v, bool):
            raise TypeError("Inputs must be integers.")


def check_non_negative(*values):
    check_int(*values)
    if any(v < 0 for v in values):
        raise ValueError("Inputs must be non-negative.")


def check_n_r(n, r):
    check_non_negative(n, r)
    if r > n:
        raise ValueError("r cannot be greater than n.")


def factorial(n):
    check_non_negative(n)
    return math.factorial(n)


def permutations(n, r):
    check_n_r(n, r)
    return math.perm(n, r)


def combinations(n, r):
    check_n_r(n, r)
    return math.comb(n, r)


def permutations_with_repetition(n, r):
    check_non_negative(n, r)
    # Python defines 0 ** 0 == 1, which matches the single empty sequence.
    return n ** r


def combinations_with_repetition(n, r):
    # Stars and bars: r identical stars and n - 1 bars (dividers between n types)
    # fill n + r - 1 positions, so the answer is C(n + r - 1, r).
    # With n = 0 types, only the empty selection (r = 0) is possible.
    check_non_negative(n, r)
    if n == 0:
        return 1 if r == 0 else 0
    return math.comb(n + r - 1, r)


def multinomial_coefficient(counts):
    # n! / (k1! * k2! * ... * km!) where n = k1 + k2 + ... + km.
    counts = list(counts)
    if not counts:
        raise ValueError("counts cannot be empty.")
    check_non_negative(*counts)
    result = math.factorial(sum(counts))
    for c in counts:
        result //= math.factorial(c)
    return result


def multiset_arrangements_count(text):
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")
    # Distinct arrangements of a word = multinomial of its letter counts,
    # e.g. MISSISSIPPI -> 11! / (1! * 4! * 4! * 2!) = 34650.
    freq = dict(Counter(text))
    if not freq:
        return 1, freq
    return multinomial_coefficient(freq.values()), freq


def verify_binomial_identities(n, r):
    check_n_r(n, r)
    c_nr = math.comb(n, r)
    c_sym = math.comb(n, n - r)
    # Pascal's rule C(n, r) = C(n-1, r-1) + C(n-1, r) only applies to interior entries;
    # at r = 0 or r = n one of the two terms would not exist. pascal_verified is None then.
    pascal_applicable = 1 <= r <= n - 1
    if pascal_applicable:
        pascal_sum = math.comb(n - 1, r - 1) + math.comb(n - 1, r)
        pascal_note = f"C({n - 1},{r - 1}) + C({n - 1},{r}) = {pascal_sum}"
    else:
        pascal_sum = None
        pascal_note = "Pascal's identity applies to interior elements where 1 <= r <= n - 1."
    row_sum = sum(math.comb(n, k) for k in range(n + 1))
    return {
        "n": n,
        "r": r,
        "c_nr": c_nr,
        "c_sym": c_sym,
        "symmetry_verified": c_nr == c_sym,
        "pascal_applicable": pascal_applicable,
        "pascal_verified": (pascal_sum == c_nr) if pascal_applicable else None,
        "pascal_note": pascal_note,
        "row_sum_value": row_sum,
        "power_of_two": 2 ** n,
        "row_sum_verified": row_sum == 2 ** n,
    }


def generate_pascal_triangle(num_rows):
    check_int(num_rows)
    if num_rows < 1:
        raise ValueError("Number of rows must be at least 1.")
    # Each new row is 1, then the sums of neighbouring pairs in the row above, then 1.
    triangle = [[1]]
    for _ in range(num_rows - 1):
        prev = triangle[-1]
        triangle.append([1] + [a + b for a, b in zip(prev, prev[1:])] + [1])
    return triangle


def binomial_expansion_terms(n, a, b):
    check_int(n, a, b)
    if n < 0:
        raise ValueError("Exponent n must be non-negative.")
    # Binomial theorem: (a*x + b*y)^n = sum over k of C(n, k) * a^(n-k) * b^k * x^(n-k) * y^k.
    # Each term is returned as (coefficient, power of x, power of y).
    return [(math.comb(n, k) * a ** (n - k) * b ** k, n - k, k) for k in range(n + 1)]


def term_variables(x_pow, y_pow):
    # (2, 1) -> "x^2*y". Returns "" for the constant term (both powers 0).
    parts = [v if p == 1 else f"{v}^{p}" for v, p in (("x", x_pow), ("y", y_pow)) if p > 0]
    return "*".join(parts)


def format_binomial_expansion(terms):
    # Builds text like "4*x^2 - 12*x*y + 9*y^2": zero terms are skipped,
    # a coefficient of 1 is hidden, and only the first term gets a bare "-" sign.
    parts = []
    for coeff, x_pow, y_pow in terms:
        if coeff == 0:
            continue
        variables = term_variables(x_pow, y_pow)
        size = abs(coeff)
        if not variables:
            body = str(size)
        elif size == 1:
            body = variables
        else:
            body = f"{size}*{variables}"
        if parts:
            sign = " - " if coeff < 0 else " + "
        else:
            sign = "-" if coeff < 0 else ""
        parts.append(sign + body)
    return "".join(parts) or "0"


def binomial_label(n, a, b):
    # Reuses the formatter on the two input terms, so a=2, b=-3 prints "(2*x - 3*y)^n".
    return f"({format_binomial_expansion([(a, 1, 0), (b, 0, 1)])})^{n}"


def _list_letters(generator, expected, n, r):
    # Lists every arrangement of the first n letters, then confirms that the list length,
    # the number of unique items and the formula all agree.
    # Limited to 8 letters because the list grows factorially (8! = 40,320 items).
    check_n_r(n, r)
    if n > len(LETTERS):
        raise ValueError(f"Listing is limited to n <= {len(LETTERS)}.")
    items = list(generator(LETTERS[:n], r))
    return items, expected(n, r), len(items) == len(set(items)) == expected(n, r)


def list_letter_permutations(n, r):
    return _list_letters(itertools.permutations, permutations, n, r)


def list_letter_combinations(n, r):
    return _list_letters(itertools.combinations, combinations, n, r)


def list_multiset_permutations(text):
    if not isinstance(text, str):
        raise TypeError("Input must be a string.")
    if len(text) > 8:
        raise ValueError("Listing is limited to 8 characters.")
    # itertools treats repeated letters as different items, so a set removes the duplicates.
    items = sorted(set(itertools.permutations(text)))
    expected, _ = multiset_arrangements_count(text)
    return items, expected, len(items) == expected


def derangements_list(n):
    # A derangement is a permutation where no item stays in its original position.
    # Returns [D(0), ..., D(n)] using D(n) = (n - 1) * (D(n-1) + D(n-2)), D(0) = 1, D(1) = 0.
    # The final slice handles n = 0, because the list always starts with two values.
    check_non_negative(n)
    values = [1, 0]
    for i in range(2, n + 1):
        values.append((i - 1) * (values[-1] + values[-2]))
    return values[:n + 1]


def derangements(n):
    return derangements_list(n)[-1]


def derangements_report(n):
    count = derangements(n)
    fact = math.factorial(n)
    # D(n) and n! are too large for float when n > 170, so divide exactly with Fraction
    # first and only convert the small result (about 1/e) to float.
    ratio = float(Fraction(count, fact))
    return {
        "derangements": count,
        "factorial": fact,
        "ratio": ratio,
        "limit": 1 / math.e,
        "difference": abs(ratio - 1 / math.e),
    }


def circular_permutations(n, r=None, allow_reflections=False):
    if r is None:
        r = n
    check_n_r(n, r)
    if not isinstance(allow_reflections, bool):
        raise TypeError("allow_reflections must be a boolean.")
    if r == 0:
        return 1
    # Rotating a circle of r items gives r copies of the same arrangement, so divide by r.
    # If mirror images also count as the same (necklaces), halve it again, but only for
    # r >= 3: with 1 or 2 items the mirror image is already the same arrangement.
    count = math.perm(n, r) // r
    if allow_reflections and r >= 3:
        count //= 2
    return count
