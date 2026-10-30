# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: tests.py - Plain-function automated verification suite

import os
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import combinatorics
import recurrence
import sympy_tools
import history_manager
import visualizer
import web_viewer


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


def test_visualizer_creates_files():
    """Validates that visualizer functions generate non-empty PNG files."""
    if not visualizer.is_matplotlib_available():
        return "Visualizer file creation (Matplotlib not installed, skipped)"
    
    p1 = visualizer.plot_factorial(5)
    assert p1 is not None
    assert os.path.exists(p1)
    assert os.path.getsize(p1) > 1000
    
    p2 = visualizer.plot_combinations(5, 2)
    assert p2 is not None
    assert os.path.exists(p2)
    assert os.path.getsize(p2) > 1000
    return "Visualizer PNG creation (valid non-empty files saved to plots/)"


def test_visualizer_big_numbers():
    """Validates that huge integers (500!) do not raise OverflowError in plotting."""
    if not visualizer.is_matplotlib_available():
        return "Visualizer big numbers (Matplotlib not installed, skipped)"
    
    # 500! has over 1,134 digits, which overflows standard float()
    p_fact = visualizer.plot_factorial(500)
    assert p_fact is not None
    assert os.path.exists(p_fact)
    
    p_perm = visualizer.plot_permutations(500, 250)
    assert p_perm is not None
    assert os.path.exists(p_perm)
    return "Visualizer big-integer safety (safe_log10 handles 500! without float overflow)"


def test_visualizer_edge_cases():
    """Validates visualizer behavior on zero and boundary values."""
    if not visualizer.is_matplotlib_available():
        return "Visualizer edge cases (Matplotlib not installed, skipped)"
    
    p_zero = visualizer.plot_factorial(0)
    assert p_zero is not None
    
    p_perm_zero = visualizer.plot_permutations(0, 0)
    assert p_perm_zero is not None
    
    p_comb_zero = visualizer.plot_combinations(0, 0)
    assert p_comb_zero is not None
    
    p_pascal_one = visualizer.plot_pascal_triangle(1)
    assert p_pascal_one is not None
    
    p_list_min = visualizer.plot_listing("perm", 1, 1, "")
    assert p_list_min is not None
    return "Visualizer boundary edge cases (n=0, 0!=1, single-row Pascal)"


def test_visualizer_graceful_when_unavailable():
    """Validates that visualizer functions degrade gracefully when matplotlib is absent."""
    orig_state = visualizer.MATPLOTLIB_AVAILABLE
    try:
        visualizer.MATPLOTLIB_AVAILABLE = False
        res = visualizer.plot_factorial(5)
        assert res is None
        res_gallery = visualizer.generate_all_demo_plots()
        assert res_gallery == []
    finally:
        visualizer.MATPLOTLIB_AVAILABLE = orig_state
    
    return "Visualizer graceful degradation (returns None when matplotlib is unavailable)"


def start_test_server():
    """Starts a local ThreadingHTTPServer on an ephemeral port (port 0) for testing."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_viewer.WebViewerHandler)
    server.daemon_threads = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def test_plot_endpoint_returns_png():
    """Validates that all 12 /plot/<op> endpoints return 200, image/png, and valid PNG magic."""
    server, port = start_test_server()
    base_url = f"http://127.0.0.1:{port}"
    
    endpoints = [
        "/plot/factorial?n=5",
        "/plot/permutations?n=5&r=3",
        "/plot/combinations?n=5&r=3",
        "/plot/comparison?n=5&r=3",
        "/plot/permrep?n=4&r=3",
        "/plot/combrep?n=4&r=3",
        "/plot/multiset?word=AAB",
        "/plot/listing?mode=perm&n=3&r=2",
        "/plot/identities?n=5&r=2",
        "/plot/pascal?rows=5",
        "/plot/recurrence?type=fib&terms=10",
        "/plot/expansion?n=3&a=1&b=1"
    ]
    
    png_magic = b"\x89PNG\r\n\x1a\n"
    
    try:
        for ep in endpoints:
            req = urllib.request.Request(base_url + ep)
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200, f"Endpoint {ep} did not return 200"
                content_type = resp.headers.get("Content-Type", "")
                assert "image/png" in content_type, f"Endpoint {ep} Content-Type was {content_type}"
                body = resp.read()
                assert body.startswith(png_magic), f"Endpoint {ep} body does not start with PNG magic"
                assert len(body) > 1000, f"Endpoint {ep} body too short ({len(body)} bytes)"
    finally:
        server.shutdown()
        server.server_close()
        
    return "Plot endpoints return valid PNG for all 12 operations (HTTP 200, magic bytes, length > 1000)"


def test_plot_endpoint_dynamic_inputs():
    """Validates dynamic plot generation for changing inputs (n=4, 5, 720) producing distinct PNGs."""
    server, port = start_test_server()
    base_url = f"http://127.0.0.1:{port}"
    png_magic = b"\x89PNG\r\n\x1a\n"
    
    try:
        with urllib.request.urlopen(f"{base_url}/plot/factorial?n=4", timeout=5) as resp:
            b4 = resp.read()
        with urllib.request.urlopen(f"{base_url}/plot/factorial?n=5", timeout=5) as resp:
            b5 = resp.read()
        with urllib.request.urlopen(f"{base_url}/plot/factorial?n=720", timeout=5) as resp:
            b720 = resp.read()
            
        assert b4.startswith(png_magic), "n=4 plot is not a valid PNG"
        assert b5.startswith(png_magic), "n=5 plot is not a valid PNG"
        assert b720.startswith(png_magic), "n=720 plot is not a valid PNG"
        
        # Verify dynamic rendering produces mutually different byte sequences
        assert b4 != b5, "n=4 and n=5 returned identical plots"
        assert b5 != b720, "n=5 and n=720 returned identical plots"
        assert b4 != b720, "n=4 and n=720 returned identical plots"
        
        assert len(b4) > 1000 and len(b5) > 1000 and len(b720) > 1000
    finally:
        server.shutdown()
        server.server_close()
        
    return "Dynamic plot inputs produce mutually distinct PNGs (n=4, n=5, n=720 without overflow)"


def test_plot_endpoint_bad_input():
    """Validates that malformed, out-of-range, or injected inputs return HTTP 400 or 404 plain text."""
    server, port = start_test_server()
    base_url = f"http://127.0.0.1:{port}"
    
    bad_cases_400 = [
        "/plot/factorial?n=-1",
        "/plot/combinations?n=3&r=5",
        "/plot/factorial",
        "/plot/factorial?n=abc",
        "/plot/recurrence?type=custom&terms=5&coeffs=5000&inits=1",
        "/plot/multiset?word=<script>",
        "/plot/listing?mode=unknown&n=3&r=2"
    ]
    
    try:
        for ep in bad_cases_400:
            try:
                urllib.request.urlopen(base_url + ep, timeout=5)
                assert False, f"Expected 400 for {ep}, but succeeded."
            except urllib.error.HTTPError as e:
                assert e.code == 400, f"Expected HTTP 400 for {ep}, got {e.code}"
                content_type = e.headers.get("Content-Type", "")
                assert "text/plain" in content_type, f"Expected text/plain for {ep}, got {content_type}"
                err_text = e.read().decode("utf-8")
                assert len(err_text) > 0, f"Expected non-empty error message for {ep}"

        # Unknown operation returns 404
        try:
            urllib.request.urlopen(f"{base_url}/plot/unknown_op?n=5", timeout=5)
            assert False, "Expected 404 for unknown operation, but succeeded."
        except urllib.error.HTTPError as e:
            assert e.code == 404, f"Expected HTTP 404 for unknown operation, got {e.code}"
            assert "text/plain" in e.headers.get("Content-Type", "")
    finally:
        server.shutdown()
        server.server_close()
        
    return "Bad plot inputs return HTTP 400 / 404 with plain-text explanation"


def test_server_serves_only_allowed_paths():
    """Validates server routing whitelist: serves index.html, rejects source files and traversal with 404."""
    server, port = start_test_server()
    base_url = f"http://127.0.0.1:{port}"
    
    try:
        # Route A: Root serves index.html
        with urllib.request.urlopen(f"{base_url}/", timeout=5) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8")
            assert "<!DOCTYPE html>" in body or "<html" in body
            
        with urllib.request.urlopen(f"{base_url}/index.html", timeout=5) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            
        # Disallowed files return 404
        disallowed = ["/main.py", "/history.txt", "/recurrence.py", "/favicon.ico", "/../main.py"]
        for path in disallowed:
            try:
                urllib.request.urlopen(f"{base_url}{path}", timeout=5)
                assert False, f"Expected 404 for {path}, but succeeded."
            except urllib.error.HTTPError as e:
                assert e.code == 404, f"Expected HTTP 404 for {path}, got {e.code}"
    finally:
        server.shutdown()
        server.server_close()
        
    return "Server security whitelist (serves index.html, blocks source files and traversal with 404)"


def test_server_binds_localhost_only():
    """Validates that the server binds exclusively to localhost (127.0.0.1) for safety."""
    assert web_viewer.HOST == "127.0.0.1", f"Expected HOST 127.0.0.1, got {web_viewer.HOST}"
    assert web_viewer.HOST != "0.0.0.0", "HOST cannot be 0.0.0.0 (security risk)"
    
    server, port = start_test_server()
    try:
        bound_ip = server.server_address[0]
        assert bound_ip == "127.0.0.1", f"Server bound to {bound_ip} instead of 127.0.0.1"
    finally:
        server.shutdown()
        server.server_close()
        
    return "Server localhost binding (127.0.0.1 only, prevents public exposure)"


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
        test_visualizer_creates_files,
        test_visualizer_big_numbers,
        test_visualizer_edge_cases,
        test_visualizer_graceful_when_unavailable,
        test_plot_endpoint_returns_png,
        test_plot_endpoint_dynamic_inputs,
        test_plot_endpoint_bad_input,
        test_server_serves_only_allowed_paths,
        test_server_binds_localhost_only
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
