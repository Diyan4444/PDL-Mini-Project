# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: tests.py - Plain-function automated verification suite

import os
import combinatorics
import recurrence
import sympy_tools
import history_manager


def test_factorial_known_answers():
    """Validates 0! = 1, 1! = 1, 5! = 120, and 10! = 3628800."""
    assert combinatorics.factorial(0) == 1
    assert combinatorics.factorial(1) == 1
    assert combinatorics.factorial(5) == 120
    assert combinatorics.factorial(10) == 3628800
    return "Factorial known answers (0!, 1!, 5!, 10!)"


def test_permutations_known_answers():
    """Validates P(5, 3) = 60, P(5, 0) = 1, and P(5, 5) = 120."""
    assert combinatorics.permutations(5, 3) == 60
    assert combinatorics.permutations(5, 0) == 1
    assert combinatorics.permutations(5, 5) == 120
    return "Permutations known answers (P(5,3)=60, P(5,0)=1, P(5,5)=120)"


def test_combinations_known_answers():
    """Validates C(5, 3) = 10, C(52, 5) = 2598960, C(5, 0) = 1, and C(5, 5) = 1."""
    assert combinatorics.combinations(5, 3) == 10
    assert combinatorics.combinations(52, 5) == 2598960
    assert combinatorics.combinations(5, 0) == 1
    assert combinatorics.combinations(5, 5) == 1
    return "Combinations known answers (C(5,3)=10, C(52,5)=2598960, C(5,0)=1, C(5,5)=1)"


def test_repetition_variants():
    """Validates permutations and combinations with repetition.
    
    5^3 = 125, 0^0 = 1, C(5+3-1, 3) = C(7, 3) = 35.
    For n = 0: r = 0 gives 1, r = 3 gives 0.
    """
    assert combinatorics.permutations_with_repetition(5, 3) == 125
    assert combinatorics.permutations_with_repetition(0, 0) == 1
    assert combinatorics.permutations_with_repetition(0, 4) == 0
    
    assert combinatorics.combinations_with_repetition(5, 3) == 35
    assert combinatorics.combinations_with_repetition(0, 0) == 1
    assert combinatorics.combinations_with_repetition(0, 3) == 0
    assert combinatorics.combinations_with_repetition(4, 0) == 1
    return "Repetition variants (5^3=125, 0^0=1, C(7,3)=35, n=0 cases)"


def test_multiset_arrangements():
    """Validates multiset permutation counting on MISSISSIPPI (=34650) and AAB (=3)."""
    miss_count, miss_freq = combinatorics.multiset_arrangements_count("MISSISSIPPI")
    assert miss_count == 34650
    assert miss_freq == {"M": 1, "I": 4, "S": 4, "P": 2}
    
    aab_count, aab_freq = combinatorics.multiset_arrangements_count("AAB")
    assert aab_count == 3
    assert aab_freq == {"A": 2, "B": 1}
    return "Multiset arrangements (MISSISSIPPI=34650, AAB=3)"


def test_binomial_identities_and_row_sums():
    """Validates symmetry, Pascal's identity, and row sums = 2^n for n=0..20."""
    # Test symmetry for various values
    test_cases = [(5, 2), (10, 4), (12, 7), (15, 0), (20, 10)]
    for n, r in test_cases:
        rep = combinatorics.verify_binomial_identities(n, r)
        assert rep["symmetry_verified"] is True
        if rep["pascal_applicable"]:
            assert rep["pascal_verified"] is True
    
    # Test row sums for all n from 0 to 20
    for n in range(21):
        computed_sum = sum(combinatorics.combinations(n, k) for k in range(n + 1))
        assert computed_sum == (2 ** n)
    
    return "Binomial identities (symmetry, Pascal's identity, row sums = 2^n for n=0..20)"


def test_pascal_triangle_generation():
    """Validates Pascal's triangle construction and row 5 = [1, 5, 10, 10, 5, 1] with sum 32."""
    tri = combinatorics.generate_pascal_triangle(6)
    row_5 = tri[5]
    assert row_5 == [1, 5, 10, 10, 5, 1]
    assert sum(row_5) == 32
    assert tri[0] == [1]
    assert tri[1] == [1, 1]
    return "Pascal's triangle generation (row 5 = [1, 5, 10, 10, 5, 1], sum 32)"


def test_binomial_expansion():
    """Validates expansion of (x + y)^3 and (2*x - 3*y)^2."""
    terms_cube = combinatorics.binomial_expansion_terms(3, 1, 1)
    coeffs_cube = [t[0] for t in terms_cube]
    assert coeffs_cube == [1, 3, 3, 1]
    formatted_cube = combinatorics.format_binomial_expansion(terms_cube)
    assert "x^3" in formatted_cube
    assert "y^3" in formatted_cube
    
    terms_quad = combinatorics.binomial_expansion_terms(2, 2, -3)
    # (2x - 3y)^2 = 4x^2 - 12xy + 9y^2
    coeffs_quad = [t[0] for t in terms_quad]
    assert coeffs_quad == [4, -12, 9]
    return "Binomial expansion ((x+y)^3 and (2*x - 3*y)^2)"


def test_listing_and_uniqueness():
    """Validates listing functions using itertools, tuple storage, and set uniqueness."""
    perms_list, p_theo, p_match = combinatorics.list_letter_permutations(4, 2)
    assert len(perms_list) == 12
    assert p_theo == 12
    assert p_match is True
    assert isinstance(perms_list[0], tuple)
    
    combs_list, c_theo, c_match = combinatorics.list_letter_combinations(4, 2)
    assert len(combs_list) == 6
    assert c_theo == 6
    assert c_match is True
    assert isinstance(combs_list[0], tuple)
    
    multi_list, m_theo, m_match = combinatorics.list_multiset_permutations("AAB")
    assert len(multi_list) == 3
    assert m_theo == 3
    assert m_match is True
    return "Arrangement and combination listing with set uniqueness"


def test_recurrence_sequences():
    """Validates Fibonacci, factorial recurrence, and custom order 2 recurrence."""
    fib_10 = recurrence.fibonacci_sequence(10)
    assert fib_10 == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    
    fact_6 = recurrence.factorial_recurrence(6)
    assert fact_6 == [1, 1, 2, 6, 24, 120]
    
    # Custom order 2 recurrence reproducing Fibonacci: a(n) = 1*a(n-1) + 1*a(n-2) with (0, 1)
    custom_fib = recurrence.custom_linear_recurrence(2, [1, 1], (0, 1), 10)
    assert custom_fib == fib_10
    
    # Custom order 1: a(n) = 3 * a(n-1) with a(0) = 2
    geom = recurrence.custom_linear_recurrence(1, [3], (2,), 4)
    assert geom == [2, 6, 18, 54]
    return "Recurrence sequences (Fibonacci, factorial rec, custom order 1 & 2)"


def test_invalid_input_rejection():
    """Validates proper error raising on invalid and boundary inputs."""
    # Negative factorial
    try:
        combinatorics.factorial(-1)
        assert False, "Negative factorial should raise ValueError"
    except ValueError:
        pass
    
    # r > n for ordinary permutations
    try:
        combinatorics.permutations(3, 5)
        assert False, "r > n for P(n,r) should raise ValueError"
    except ValueError:
        pass
    
    # r > n for ordinary combinations
    try:
        combinatorics.combinations(3, 5)
        assert False, "r > n for C(n,r) should raise ValueError"
    except ValueError:
        pass
    
    # Zero trailing coefficient in custom recurrence
    try:
        recurrence.custom_linear_recurrence(2, [1, 0], (1, 1), 5)
        assert False, "Trailing zero coefficient should raise ValueError"
    except ValueError:
        pass
    
    # Mismatched order counts
    try:
        recurrence.custom_linear_recurrence(2, [1, 1, 1], (1, 1), 5)
        assert False, "Mismatched coefficient length should raise ValueError"
    except ValueError:
        pass
    
    return "Input validation and error rejection (negatives, r > n, invalid orders)"


def test_history_persistence():
    """Validates persistent history saving and reading round trip."""
    temp_hist_file = "test_run_temp_history.txt"
    temp_path = history_manager.get_history_file_path(temp_hist_file)
    
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    try:
        ok1 = history_manager.save_history_record("TEST_PERM", "n=5, r=3", "60", filename=temp_hist_file)
        ok2 = history_manager.save_history_record("TEST_COMB", "n=5, r=2", "10", filename=temp_hist_file)
        assert ok1 is True and ok2 is True
        
        records, skipped = history_manager.read_history_records(filename=temp_hist_file)
        assert len(records) == 2
        assert skipped == 0
        assert records[0]["operation"] == "TEST_PERM"
        assert records[0]["result"] == "60"
        
        matches, total, _ = history_manager.search_history_records("COMB", filename=temp_hist_file)
        assert len(matches) == 1
        assert matches[0]["operation"] == "TEST_COMB"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return "History persistence and round-trip verification"


def test_sympy_integration_if_present():
    """Validates SymPy verification functions if SymPy is installed."""
    if not sympy_tools.is_sympy_available():
        return "SymPy not installed (optional integration skipped cleanly)"
    
    # Test factorial check
    ok_f, val_f, _ = sympy_tools.sympy_verify_factorial(6, 720)
    assert ok_f is True
    assert val_f == 720
    
    # Test combination check
    ok_c, val_c, _ = sympy_tools.sympy_verify_combination(6, 2, 15)
    assert ok_c is True
    assert val_c == 15
    
    # Test expansion check
    terms = combinatorics.binomial_expansion_terms(3, 1, 1)
    ok_e, _, _ = sympy_tools.sympy_verify_expansion(3, 1, 1, terms)
    assert ok_e is True
    
    # Test rsolve closed form for Fibonacci
    fib_10 = recurrence.fibonacci_sequence(10)
    ok_r, _, checks, _ = sympy_tools.sympy_closed_form_recurrence("fibonacci", 2, [1, 1], (0, 1), fib_10)
    assert ok_r is True
    assert len(checks) == 10
    for chk in checks:
        assert chk["matched"] is True
    
    return "SymPy symbolic verification (factorial, binomial, expansion, rsolve)"


def run_all_tests():
    """Executes all test functions and returns a summary dictionary."""
    test_functions = [
        test_factorial_known_answers,
        test_permutations_known_answers,
        test_combinations_known_answers,
        test_repetition_variants,
        test_multiset_arrangements,
        test_binomial_identities_and_row_sums,
        test_pascal_triangle_generation,
        test_binomial_expansion,
        test_listing_and_uniqueness,
        test_recurrence_sequences,
        test_invalid_input_rejection,
        test_history_persistence,
        test_sympy_integration_if_present,
    ]
    
    passed_count = 0
    failed_count = 0
    results = []
    
    print("=" * 70)
    print("COMBINATORIAL COUNTING ANALYZER - AUTOMATED TEST SUITE")
    print("=" * 70)
    
    for tf in test_functions:
        name = tf.__name__
        try:
            desc = tf()
            passed_count = passed_count + 1
            print("[PASS] " + desc)
            results.append({"name": name, "status": "PASS", "description": desc})
        except AssertionError as e:
            failed_count = failed_count + 1
            print("[FAIL] " + name + " (AssertionError: " + str(e) + ")")
            results.append({"name": name, "status": "FAIL", "description": str(e)})
        except Exception as e:
            failed_count = failed_count + 1
            print("[FAIL] " + name + " (Exception: " + str(e) + ")")
            results.append({"name": name, "status": "FAIL", "description": str(e)})
    
    total = passed_count + failed_count
    print("=" * 70)
    print("TEST SUMMARY: " + str(passed_count) + "/" + str(total) + " tests passed. (" + str(failed_count) + " failed)")
    print("=" * 70)
    
    return {
        "passed": passed_count,
        "failed": failed_count,
        "total": total,
        "results": results
    }


if __name__ == "__main__":
    run_all_tests()
