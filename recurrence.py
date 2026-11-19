# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Generates the terms of recurrence relations one by one.
# Finding a closed-form formula for a(n) is a separate job, done in sympy_tools.py.

from combinatorics import check_int

# Term limit shared by the CLI, the web API and the charts.
MAX_TERMS = 50


def check_terms(num_terms):
    check_int(num_terms)
    if not 1 <= num_terms <= MAX_TERMS:
        raise ValueError(f"num_terms must be between 1 and {MAX_TERMS}.")


def custom_linear_recurrence(order_k, coefficients, initial_values, num_terms):
    # a(n) = c1*a(n-1) + c2*a(n-2) + ... + ck*a(n-k), starting from a(0) .. a(k-1).
    # The last coefficient ck must be non-zero, otherwise the order is really less than k.
    check_int(order_k, *coefficients, *initial_values)
    check_terms(num_terms)
    if order_k < 1:
        raise ValueError("Order k must be at least 1.")
    if len(coefficients) != order_k or len(initial_values) != order_k:
        raise ValueError(f"Exactly {order_k} coefficients and {order_k} initial values are required.")
    if coefficients[-1] == 0:
        raise ValueError(f"The trailing coefficient c{order_k} must be non-zero.")
    seq = list(initial_values)
    while len(seq) < num_terms:
        # seq[-1 - i] is a(n - 1 - i), which is multiplied by coefficient c(i + 1).
        seq.append(sum(c * seq[-1 - i] for i, c in enumerate(coefficients)))
    return seq[:num_terms]


def fibonacci_sequence(num_terms):
    # F(n) = F(n-1) + F(n-2) with F(0) = 0, F(1) = 1.
    return custom_linear_recurrence(2, [1, 1], (0, 1), num_terms)


def factorial_recurrence(num_terms):
    # a(0) = 1, a(n) = n * a(n-1). The multiplier changes with n, so this cannot
    # reuse custom_linear_recurrence, which needs constant coefficients.
    check_terms(num_terms)
    seq = [1]
    for n in range(1, num_terms):
        seq.append(n * seq[-1])
    return seq
