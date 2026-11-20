# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Generates the terms of two recurrence relations one by one.
# Finding a closed-form formula for Fibonacci is a separate job, done in sympy_tools.py.

from combinatorics import check_int

# Term limit shared by the CLI, the web API and the charts.
MAX_TERMS = 50


def check_terms(num_terms):
    check_int(num_terms)
    if not 1 <= num_terms <= MAX_TERMS:
        raise ValueError(f"num_terms must be between 1 and {MAX_TERMS}.")


def fibonacci_sequence(num_terms):
    # F(0) = 0, F(1) = 1, and every later term is the sum of the previous two.
    check_terms(num_terms)
    seq = [0, 1]
    while len(seq) < num_terms:
        seq.append(seq[-1] + seq[-2])
    # The slice handles num_terms = 1, because the list always starts with two values.
    return seq[:num_terms]


def factorial_recurrence(num_terms):
    # a(0) = 1, a(n) = n * a(n-1): each term multiplies the previous one by its position.
    check_terms(num_terms)
    seq = [1]
    for n in range(1, num_terms):
        seq.append(n * seq[-1])
    return seq
