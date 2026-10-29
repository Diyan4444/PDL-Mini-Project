# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: recurrence.py - Numerical generation of recurrence sequences

def fibonacci_sequence(num_terms):
    """Generates the first num_terms of the Fibonacci sequence.
    
    Recurrence: F(0) = 0, F(1) = 1, F(n) = F(n - 1) + F(n - 2)
    Valid terms range: 1 <= num_terms <= 50.
    Returns a list of integer terms.
    """
    if not isinstance(num_terms, int):
        raise TypeError("num_terms must be an integer.")
    if num_terms < 1 or num_terms > 50:
        raise ValueError("num_terms must be between 1 and 50.")
    
    if num_terms == 1:
        return [0]
    
    sequence = [0, 1]
    for i in range(2, num_terms):
        next_val = sequence[i - 1] + sequence[i - 2]
        sequence.append(next_val)
    
    return sequence


def factorial_recurrence(num_terms):
    """Generates terms using the factorial recurrence relation.
    
    Recurrence: a(0) = 1, a(n) = n * a(n - 1) for n >= 1
    Valid terms range: 1 <= num_terms <= 50.
    Returns a list of integer terms corresponding to a(0), a(1), ..., a(num_terms - 1).
    """
    if not isinstance(num_terms, int):
        raise TypeError("num_terms must be an integer.")
    if num_terms < 1 or num_terms > 50:
        raise ValueError("num_terms must be between 1 and 50.")
    
    sequence = [1]
    for n in range(1, num_terms):
        next_val = n * sequence[n - 1]
        sequence.append(next_val)
    
    return sequence


def pascal_recurrence_row(n):
    """Computes row n of Pascal's triangle using the additive recurrence relation.
    
    Recurrence: C(n, k) = C(n - 1, k - 1) + C(n - 1, k)
    Boundary conditions: C(n, 0) = 1, C(n, n) = 1
    Returns row n as a list of integers.
    """
    if not isinstance(n, int):
        raise TypeError("Row index n must be an integer.")
    if n < 0 or n > 20:
        raise ValueError("Row index n must be between 0 and 20.")
    
    if n == 0:
        return [1]
    
    prev_row = [1]
    for current_n in range(1, n + 1):
        new_row = [1]
        for k in range(1, current_n):
            new_row.append(prev_row[k - 1] + prev_row[k])
        new_row.append(1)
        prev_row = new_row
    
    return prev_row


def custom_linear_recurrence(order_k, coefficients, initial_values, num_terms):
    """Generates terms for a custom linear recurrence with constant coefficients.
    
    Relation: a(n) = c1 * a(n - 1) + c2 * a(n - 2) + ... + ck * a(n - k)
    
    Parameters:
      order_k: Integer order (1 <= order_k <= 5).
      coefficients: List of k integers [c1, c2, ..., ck] with absolute values <= 1000.
                    The last coefficient ck must be non-zero to maintain true order k.
      initial_values: Tuple of k integers (a0, a1, ..., a_{k-1}) with absolute values <= 1000.
      num_terms: Total count of terms to generate (1 <= num_terms <= 50).
      
    Returns a list of integers representing a(0), a(1), ..., a(num_terms - 1).
    Note: Numerical term generation is separate from symbolic closed-form solving.
    """
    if not isinstance(order_k, int):
        raise TypeError("order_k must be an integer.")
    if order_k < 1 or order_k > 5:
        raise ValueError("Order k must be between 1 and 5.")
    
    if not isinstance(coefficients, list):
        raise TypeError("coefficients must be provided as a list.")
    if len(coefficients) != order_k:
        raise ValueError("Exactly " + str(order_k) + " coefficients are required for order " + str(order_k) + ".")
    
    for c in coefficients:
        if not isinstance(c, int):
            raise TypeError("All coefficients must be integers.")
        if abs(c) > 1000:
            raise ValueError("Coefficients must satisfy |c| <= 1000.")
    
    if coefficients[-1] == 0:
        raise ValueError("The trailing coefficient c" + str(order_k) + " must be non-zero for order " + str(order_k) + ".")
    
    if not isinstance(initial_values, tuple):
        raise TypeError("initial_values must be provided as a tuple.")
    if len(initial_values) != order_k:
        raise ValueError("Exactly " + str(order_k) + " initial values are required for order " + str(order_k) + ".")
    
    for val in initial_values:
        if not isinstance(val, int):
            raise TypeError("All initial values must be integers.")
        if abs(val) > 1000:
            raise ValueError("Initial values must satisfy |val| <= 1000.")
    
    if not isinstance(num_terms, int):
        raise TypeError("num_terms must be an integer.")
    if num_terms < 1 or num_terms > 50:
        raise ValueError("num_terms must be between 1 and 50.")
    
    # Base case: if requested terms are fewer than or equal to k
    if num_terms <= order_k:
        return list(initial_values[:num_terms])
    
    sequence = list(initial_values)
    for n in range(order_k, num_terms):
        next_val = 0
        for i in range(order_k):
            coeff = coefficients[i]
            prev_term = sequence[n - 1 - i]
            next_val = next_val + (coeff * prev_term)
        sequence.append(next_val)
    
    return sequence
