# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Automated tests. Run with: python tests.py (also menu option 16 in main.py).
# Plain functions, no test framework: each test_* returns a description when it passes
# and raises (usually AssertionError) when it fails. To add a test, write a function
# and add it to the TESTS list at the bottom.

import os
import json
import math
import itertools
import threading
import contextlib
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import combinatorics as cb
import recurrence
import sympy_tools
import visualizer
import web_viewer

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def raises(error, func, *args, **kwargs):
    # True if func(*args) raises the given exception type.
    try:
        func(*args, **kwargs)
    except error:
        return True
    return False


@contextlib.contextmanager
def test_server():
    # Runs the real web server on a free port (port 0) in a background thread and
    # yields its base URL; the server is shut down when the "with" block ends.
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_viewer.WebViewerHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def request(url, method="GET", headers=None, data=None):
    # Returns (status, content type, body) for every response, including 4xx/5xx errors,
    # which urllib would otherwise raise as exceptions.
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def get_json(url):
    status, _, body = request(url)
    return status, json.loads(body)


def test_basic_counts():
    assert [cb.factorial(n) for n in (0, 1, 5, 10)] == [1, 1, 120, 3628800]
    assert [cb.permutations(5, r) for r in (0, 3, 5)] == [1, 60, 120]
    assert [cb.combinations(5, 0), cb.combinations(5, 3), cb.combinations(52, 5)] == [1, 10, 2598960]
    assert cb.permutations_with_repetition(5, 3) == 125
    assert cb.permutations_with_repetition(0, 0) == 1 and cb.permutations_with_repetition(0, 4) == 0
    assert cb.combinations_with_repetition(5, 3) == 35
    assert cb.combinations_with_repetition(0, 0) == 1 and cb.combinations_with_repetition(0, 3) == 0
    assert cb.combinations_with_repetition(4, 0) == 1
    return "Factorial, P, C and repetition variants (known answers and n = 0 cases)"


def test_multiset_and_multinomial():
    assert cb.multiset_arrangements_count("MISSISSIPPI") == (34650, {"M": 1, "I": 4, "S": 4, "P": 2})
    assert cb.multiset_arrangements_count("AAB") == (3, {"A": 2, "B": 1})
    assert cb.multiset_arrangements_count("") == (1, {})
    assert cb.multinomial_coefficient([1, 4, 4, 2]) == 34650
    assert cb.multinomial_coefficient([5]) == 1
    assert raises(ValueError, cb.multinomial_coefficient, [])
    assert raises(ValueError, cb.multinomial_coefficient, [3, -1])
    assert raises(TypeError, cb.multinomial_coefficient, [2, False])
    return "Multiset arrangements and multinomial coefficient (MISSISSIPPI = 34650)"


def test_binomial_identities_and_pascal():
    for n, r in [(0, 0), (5, 2), (10, 4), (12, 7), (15, 0), (20, 10), (300, 150)]:
        rep = cb.verify_binomial_identities(n, r)
        assert rep["symmetry_verified"] and rep["row_sum_verified"]
        assert rep["pascal_verified"] is (True if 1 <= r <= n - 1 else None)
    triangle = cb.generate_pascal_triangle(15)
    assert triangle[0] == [1] and triangle[5] == [1, 5, 10, 10, 5, 1]
    assert all(row == [math.comb(i, k) for k in range(i + 1)] for i, row in enumerate(triangle))
    return "Binomial identities and Pascal's triangle (15 rows checked against C(n, k))"


def test_binomial_expansion():
    assert [c for c, _, _ in cb.binomial_expansion_terms(3, 1, 1)] == [1, 3, 3, 1]
    assert cb.format_binomial_expansion(cb.binomial_expansion_terms(3, 1, 1)) == "x^3 + 3*x^2*y + 3*x*y^2 + y^3"
    assert cb.format_binomial_expansion(cb.binomial_expansion_terms(2, 2, -3)) == "4*x^2 - 12*x*y + 9*y^2"
    assert cb.format_binomial_expansion(cb.binomial_expansion_terms(2, -1, 0)) == "x^2"
    assert cb.format_binomial_expansion(cb.binomial_expansion_terms(0, 3, 4)) == "1"
    assert cb.binomial_label(3, 2, -3) == "(2*x - 3*y)^3"
    assert cb.binomial_label(2, 1, 1) == "(x + y)^2"
    return "Binomial expansion and formatting ((x+y)^3, (2x-3y)^2, zero and n = 0 cases)"


def test_listing():
    items, expected, ok = cb.list_letter_permutations(4, 2)
    assert len(items) == expected == 12 and ok and items[0] == ("A", "B")
    items, expected, ok = cb.list_letter_combinations(4, 2)
    assert len(items) == expected == 6 and ok
    items, expected, ok = cb.list_multiset_permutations("AAB")
    assert items == [("A", "A", "B"), ("A", "B", "A"), ("B", "A", "A")] and expected == 3 and ok
    assert raises(ValueError, cb.list_letter_permutations, 9, 2)
    assert raises(ValueError, cb.list_multiset_permutations, "ABCDEFGHI")
    return "Listing permutations, combinations and multiset arrangements"


def test_recurrences():
    fib = recurrence.fibonacci_sequence(10)
    assert fib == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    assert recurrence.fibonacci_sequence(1) == [0]
    assert recurrence.factorial_recurrence(6) == [1, 1, 2, 6, 24, 120]
    assert recurrence.fibonacci_sequence(2) == [0, 1]
    assert recurrence.factorial_recurrence(1) == [1]
    assert raises(ValueError, recurrence.fibonacci_sequence, 0)
    assert raises(ValueError, recurrence.fibonacci_sequence, 51)
    assert raises(ValueError, recurrence.factorial_recurrence, 51)
    return "Recurrences (Fibonacci, factorial recurrence, 1 and 2 terms, invalid input)"


def test_derangements():
    # Independent check: count permutations of 0..n-1 where no item stays in its position.
    for n in range(8):
        brute = sum(all(p[i] != i for i in range(n)) for p in itertools.permutations(range(n)))
        assert cb.derangements(n) == brute
    assert cb.derangements_list(6) == [1, 0, 1, 2, 9, 44, 265]
    assert cb.derangements_list(0) == [1]
    for n in (10, 171, 1000):
        assert abs(cb.derangements_report(n)["ratio"] - 1 / math.e) < 1e-6
    return "Derangements (brute force for n <= 7, ratio -> 1/e up to n = 1000)"


def test_circular_permutations():
    assert cb.circular_permutations(4) == 6 and cb.circular_permutations(5, 5) == 24
    assert cb.circular_permutations(5, 3) == 20 and cb.circular_permutations(6, 4) == 90
    assert cb.circular_permutations(5, 1) == 5 and cb.circular_permutations(1, 1) == 1
    assert cb.circular_permutations(5, 0) == 1
    assert cb.circular_permutations(5, 5, True) == 12 and cb.circular_permutations(5, 3, True) == 10
    assert cb.circular_permutations(2, 2, True) == 1
    return "Circular permutations (rotations, reflections, r = 0 and r = 1)"


def test_invalid_input_rejection():
    assert raises(ValueError, cb.factorial, -1)
    assert raises(ValueError, cb.permutations, 3, 5)
    assert raises(ValueError, cb.combinations, 3, 5)
    assert raises(ValueError, cb.circular_permutations, 3, 5)
    assert raises(ValueError, cb.derangements, -1)
    for bad in (True, 2.0, "3"):
        assert raises(TypeError, cb.factorial, bad)
        assert raises(TypeError, cb.combinations, 5, bad)
        assert raises(TypeError, recurrence.fibonacci_sequence, bad)
    assert raises(TypeError, cb.circular_permutations, 5, 3, "yes")
    return "Invalid input rejection (negatives, r > n, booleans, floats, strings)"


def test_sympy():
    if not sympy_tools.SYMPY_AVAILABLE:
        assert sympy_tools.run_all_symbolic_checks()["available"] is False
        return "SymPy not installed (optional checks skipped)"
    assert sympy_tools.verify_factorial(6, 720)[0]
    assert sympy_tools.verify_combination(6, 2, 15)[0]
    assert not sympy_tools.verify_combination(6, 2, 16)[0]
    assert sympy_tools.verify_expansion(3, 2, -3, cb.binomial_expansion_terms(3, 2, -3))[0]
    ok, _, checks, _ = sympy_tools.fibonacci_closed_form(recurrence.fibonacci_sequence(10))
    assert ok and len(checks) == 10 and all(c["matched"] for c in checks)
    ok, _, checks, _ = sympy_tools.fibonacci_closed_form([0, 1, 1, 2, 4])
    assert not checks[-1]["matched"]
    assert all(r["verified"] for r in sympy_tools.run_all_symbolic_checks()["results"])
    return "SymPy verification (factorial, binomial, expansion, rsolve)"


def test_visualizer():
    if not visualizer.MATPLOTLIB_AVAILABLE:
        return "Matplotlib not installed (charts skipped)"
    paths = [path for _, path in visualizer.generate_all_demo_plots()]
    assert len(paths) == 14
    # Delete the gallery files so repeated test runs don't fill up plots/.
    for path in paths:
        assert os.path.getsize(path) > 1000
        os.remove(path)
    cases = [
        (visualizer.plot_factorial, (0,)), (visualizer.plot_factorial, (1000,)),
        (visualizer.plot_permutations, (0, 0)), (visualizer.plot_permutations, (500, 250)),
        (visualizer.plot_combinations, (0, 0)), (visualizer.plot_combinations, (1000, 500)),
        (visualizer.plot_comparison, (0, 0)), (visualizer.plot_perm_with_repetition, (1000, 1000)),
        (visualizer.plot_comb_with_repetition, (0, 3)), (visualizer.plot_comb_with_repetition, (1000, 1000)),
        (visualizer.plot_listing, ("comb", 1, 1)), (visualizer.plot_listing, ("multiset", 0, 0, "AAB")),
        (visualizer.plot_binomial_identities, (0, 0)), (visualizer.plot_binomial_identities, (1000, 3)),
        (visualizer.plot_pascal_triangle, (1,)), (visualizer.plot_recurrence, ("factorial", [1], "one term")),
        (visualizer.plot_binomial_expansion, (20, 10, -10)), (visualizer.plot_binomial_expansion, (0, 0, 0)),
        (visualizer.plot_derangements, (0,)), (visualizer.plot_derangements, (1000,)),
        (visualizer.plot_circular_permutations, (0,)), (visualizer.plot_circular_permutations, (12, 10, True)),
    ]
    for func, args in cases:
        png = func(*args, as_bytes=True)
        assert png.startswith(PNG_MAGIC), f"{func.__name__}{args} did not return a PNG"
    return "All 14 demo charts plus edge cases (n = 0, n = 1000, huge coefficients)"


def test_visualizer_without_matplotlib():
    # Pretend matplotlib is missing, then restore the real value.
    original = visualizer.MATPLOTLIB_AVAILABLE
    visualizer.MATPLOTLIB_AVAILABLE = False
    try:
        assert visualizer.plot_factorial(5) is None
        assert visualizer.generate_all_demo_plots() == []
    finally:
        visualizer.MATPLOTLIB_AVAILABLE = original
    return "Charts return None cleanly when matplotlib is missing"


def test_server_routes():
    assert web_viewer.HOST == "127.0.0.1"
    with test_server() as base:
        status, ctype, body = request(base + "/")
        assert status == 200 and "text/html" in ctype and b"<html" in body.lower()
        for path in ("/main.py", "/README.md", "/favicon.ico", "/../main.py", "/api/unknown", "/api/history"):
            assert request(base + path)[0] == 404, path
    return "Server serves index.html only and returns 404 for everything else"


def test_api_calc():
    with test_server() as base:
        # (query, field in the JSON reply, expected value)
        expected = [
            ("op=factorial&n=5", "result", "120"),
            ("op=permutations&n=5&r=3", "result", "60"),
            ("op=combinations&n=5&r=3", "result", "10"),
            ("op=comparison&n=5&r=3", "is_verified", True),
            ("op=permrep&n=5&r=3", "result", "125"),
            ("op=combrep&n=5&r=3", "result", "35"),
            ("op=multiset&word=MISSISSIPPI", "result", "34650"),
            ("op=listing&mode=perm&n=4&r=2", "count", 12),
            ("op=listing&mode=multi&word=AAB", "items", ["AAB", "ABA", "BAA"]),
            ("op=pascal&rows=5", "triangle", [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]),
            ("op=recurrence&type=fib&terms=5", "sequence", ["0", "1", "1", "2", "3"]),
            ("op=recurrence&type=fact&terms=6", "sequence", ["1", "1", "2", "6", "24", "120"]),
            ("op=expansion&n=2&a=2&b=-3", "formatted", "4*x^2 - 12*x*y + 9*y^2"),
            ("op=derangements&n=500", "result", str(cb.derangements(500))),
            ("op=circular&n=5&r=3&reflections=1", "result", "10"),
            ("op=circular&n=5", "result", "24"),
        ]
        for query, field, value in expected:
            status, data = get_json(f"{base}/api/calc?{query}")
            assert status == 200 and data["success"] and data[field] == value, query
        status, data = get_json(f"{base}/api/calc?op=identities&n=6&r=3")
        assert data["report"]["c_nr"] == "20" and data["report"]["row_sum_verified"] is True
        status, data = get_json(f"{base}/api/calc?op=derangements&n=5")
        assert abs(data["ratio"] - 44 / 120) < 1e-12 and data["ratio_approx_1_over_e"] == 1 / math.e

        bad = [
            ("op=factorial&n=-5", 400), ("op=factorial", 400), ("op=factorial&n=abc", 400), ("", 400),
            ("op=nope&n=1", 404), ("op=combinations&n=3&r=5", 400), ("op=multiset&word=" + "A" * 51, 400),
            ("op=multiset&word=a%20b", 400), ("op=listing&mode=x", 400), ("op=recurrence&type=x&terms=5", 400),
            ("op=recurrence&type=custom&terms=5", 400), ("op=recurrence&type=fib&terms=51", 400),
        ]
        for query, code in bad:
            status, data = get_json(f"{base}/api/calc?{query}")
            assert status == code and data["success"] is False, query
    return "/api/calc returns correct results for all 14 operations and 400/404 for bad input"


def test_api_sympy():
    with test_server() as base:
        status, data = get_json(f"{base}/api/sympy")
        assert status == 200 and data["sympy"]["available"] == sympy_tools.SYMPY_AVAILABLE
    return "/api/sympy reports the SymPy checks"


def test_plot_endpoint():
    if not visualizer.MATPLOTLIB_AVAILABLE:
        return "Matplotlib not installed (plot endpoint skipped)"
    queries = [
        "factorial?n=5", "permutations?n=5&r=3", "combinations?n=5&r=3", "comparison?n=5&r=3", "permrep?n=4&r=3",
        "combrep?n=4&r=3", "multiset?word=AAB", "listing?mode=perm&n=3&r=2", "identities?n=5&r=2", "pascal?rows=5",
        "recurrence?type=fib&terms=10", "expansion?n=3&a=1&b=1", "derangements?n=1000", "circular?n=5&r=3&allow_reflections=1",
    ]
    with test_server() as base:
        images = set()
        for q in queries:
            status, ctype, body = request(f"{base}/plot/{q}")
            assert status == 200 and ctype == "image/png" and body.startswith(PNG_MAGIC), q
            images.add(body)
        # Every chart should be different, proving the inputs actually reach the plot.
        assert len(images) == len(queries)
        for q in ("factorial?n=-1", "combinations?n=3&r=5", "factorial", "multiset?word=<script>", "listing?mode=x"):
            status, ctype, body = request(f"{base}/plot/{q}")
            assert status == 400 and "text/plain" in ctype and body, q
        assert request(f"{base}/plot/unknown?n=5")[0] == 404
    return "/plot returns a distinct PNG for all 14 operations and 400/404 for bad input"


TESTS = [
    test_basic_counts,
    test_multiset_and_multinomial,
    test_binomial_identities_and_pascal,
    test_binomial_expansion,
    test_listing,
    test_recurrences,
    test_derangements,
    test_circular_permutations,
    test_invalid_input_rejection,
    test_sympy,
    test_visualizer,
    test_visualizer_without_matplotlib,
    test_server_routes,
    test_api_calc,
    test_api_sympy,
    test_plot_endpoint,
]


def run_all_tests():
    passed = 0
    print("=" * 70)
    print("COMBINATORIAL COUNTING ANALYZER - AUTOMATED TEST SUITE")
    print("=" * 70)
    for test in TESTS:
        try:
            print("[PASS] " + test())
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {type(e).__name__} {e}")
    print("=" * 70)
    print(f"TEST SUMMARY: {passed}/{len(TESTS)} tests passed. ({len(TESTS) - passed} failed)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
