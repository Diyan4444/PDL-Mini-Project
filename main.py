# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: main.py - Interactive CLI interface, menu coordination, input validation, and formatting

import sys
import os
import combinatorics
import recurrence
import sympy_tools
import history_manager
import tests
import visualizer


def prompt_and_show_visual(plot_func, *args, **kwargs):
    """Prompts the user to generate and display a visual explanation chart."""
    if not visualizer.is_visualizer_available():
        print("  [Visualizer Note] Matplotlib is not installed. Visual explanation skipped.")
        return

    choice = get_integer_input("\nShow visual explanation? (1 = yes, 0 = no): ", 0, 1)
    if choice == 1:
        try:
            path = plot_func(*args, **kwargs)
            if path:
                print("  Saved plot to " + path)
                try:
                    if hasattr(os, "startfile"):
                        os.startfile(path)
                    else:
                        import subprocess
                        opener = "open" if sys.platform == "darwin" else "xdg-open"
                        subprocess.run([opener, path], check=False)
                except Exception:
                    pass
        except Exception as e:
            print("  [Visualizer Error] Could not generate plot: " + str(e))



def format_large_number(num):
    """Formats large integer results for clean terminal output and history.
    
    If length exceeds 60 digits: first 20 digits, '...', last 10 digits, and total count.
    """
    s = str(num)
    if len(s) > 60:
        return s[:20] + "..." + s[-10:] + " (" + str(len(s)) + " digits)"
    return s


def get_integer_input(prompt, min_val=None, max_val=None):
    """Prompts the user for a strictly validated integer within optional bounds.
    
    Rejects decimals, letters, whitespace-only, and empty strings.
    Handles Ctrl+C and Ctrl+D gracefully.
    """
    while True:
        try:
            raw = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nOperation interrupted by user. Exiting gracefully. Goodbye!")
            sys.exit(0)
        
        if not raw:
            print("  [Error] Input cannot be empty. Please enter a valid integer.")
            continue
        
        if "." in raw:
            print("  [Error] Decimals are not permitted. Please enter a whole integer.")
            continue
        
        try:
            val = int(raw)
        except ValueError:
            print("  [Error] '" + raw + "' is not a valid integer. Please try again.")
            continue
        
        if min_val is not None and val < min_val:
            print("  [Limit Hit] Minimum allowed value is " + str(min_val) + ". You entered " + str(val) + ".")
            continue
        
        if max_val is not None and val > max_val:
            print("  [Limit Hit] Maximum allowed value is " + str(max_val) + ". You entered " + str(val) + ".")
            continue
        
        return val


def get_string_input(prompt, max_len=50, allow_alnum_only=True):
    """Prompts for a string with strict length and character set validation."""
    while True:
        try:
            raw = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nOperation interrupted by user. Exiting gracefully. Goodbye!")
            sys.exit(0)
        
        if not raw:
            print("  [Error] Input cannot be empty.")
            continue
        
        if len(raw) > max_len:
            print("  [Limit Hit] Maximum allowed length is " + str(max_len) + " characters. Length was " + str(len(raw)) + ".")
            continue
        
        if allow_alnum_only and not raw.isalnum():
            print("  [Error] Only letters and digits are permitted (no spaces or special symbols).")
            continue
        
        return raw


# =============================================================================
# INDIVIDUAL MENU ACTION HANDLERS
# =============================================================================

def handle_factorial():
    print("\n--- 1. FACTORIAL (n!) ---")
    print("Formula: n! = n * (n - 1) * ... * 1, with 0! = 1 by definition.")
    n = get_integer_input("Enter non-negative integer n (0 <= n <= 1000): ", 0, 1000)
    
    result = combinatorics.factorial(n)
    display_res = format_large_number(result)
    print("\nResult:")
    print("  " + str(n) + "! = " + display_res)
    
    # Optional SymPy verification
    if sympy_tools.is_sympy_available() and n <= 100:
        _, _, note = sympy_tools.sympy_verify_factorial(n, result)
        print("  SymPy check: " + note)
    
    history_manager.save_history_record("Factorial", "n=" + str(n), display_res)
    prompt_and_show_visual(visualizer.plot_factorial, n)


def handle_permutations():
    print("\n--- 2. PERMUTATIONS P(n, r) ---")
    print("Definition: Number of ordered arrangements of r items selected from n distinct items.")
    print("Formula: P(n, r) = n! / (n - r)!   [Order matters!]")
    n = get_integer_input("Enter total items n (0 <= n <= 1000): ", 0, 1000)
    r = get_integer_input("Enter selected items r (0 <= r <= " + str(n) + "): ", 0, n)
    
    result = combinatorics.permutations(n, r)
    display_res = format_large_number(result)
    
    print("\nStep-by-step substitution:")
    print("  P(" + str(n) + ", " + str(r) + ") = " + str(n) + "! / (" + str(n) + " - " + str(r) + ")!")
    print("  P(" + str(n) + ", " + str(r) + ") = " + str(n) + "! / " + str(n - r) + "!")
    print("  Result = " + display_res)
    print("  Explanation: Selecting and arranging " + str(r) + " items from " + str(n) + " items where order is distinct.")
    
    history_manager.save_history_record("Permutations", "n=" + str(n), display_res)
    prompt_and_show_visual(visualizer.plot_permutations, n, r)


def handle_combinations():
    print("\n--- 3. COMBINATIONS C(n, r) ---")
    print("Definition: Number of un-ordered selections (subsets) of r items from n distinct items.")
    print("Formula: C(n, r) = n! / (r! * (n - r)!) = P(n, r) / r!   [Order does NOT matter!]")
    n = get_integer_input("Enter total items n (0 <= n <= 1000): ", 0, 1000)
    r = get_integer_input("Enter selected items r (0 <= r <= " + str(n) + "): ", 0, n)
    
    result = combinatorics.combinations(n, r)
    display_res = format_large_number(result)
    
    print("\nStep-by-step substitution:")
    print("  C(" + str(n) + ", " + str(r) + ") = " + str(n) + "! / (" + str(r) + "! * (" + str(n) + " - " + str(r) + ")!)")
    print("  C(" + str(n) + ", " + str(r) + ") = " + str(n) + "! / (" + str(r) + "! * " + str(n - r) + "!)")
    print("  Result = " + display_res)
    print("\nConcept Explanation (Why we divide by r!):")
    print("  Consider choosing 3 letters {A, B, C}. The 3! = 6 ordered permutations")
    print("  (ABC, ACB, BAC, BCA, CAB, CBA) all collapse into ONE single combination set.")
    print("  Dividing P(n, r) by r! removes the count of redundant re-orderings.")
    
    if sympy_tools.is_sympy_available() and n <= 100:
        _, _, note = sympy_tools.sympy_verify_combination(n, r, result)
        print("  SymPy check: " + note)
    
    history_manager.save_history_record("Combinations", "n=" + str(n) + ", r=" + str(r), display_res)
    prompt_and_show_visual(visualizer.plot_combinations, n, r)


def handle_comparison():
    print("\n--- 4. PERMUTATION VS COMBINATION COMPARISON ---")
    print("Validating the fundamental identity: P(n, r) = C(n, r) * r!")
    n = get_integer_input("Enter total items n (0 <= n <= 1000): ", 0, 1000)
    r = get_integer_input("Enter selected items r (0 <= r <= " + str(n) + "): ", 0, n)
    
    p_val = combinatorics.permutations(n, r)
    c_val = combinatorics.combinations(n, r)
    r_fact = combinatorics.factorial(r)
    check_product = c_val * r_fact
    is_valid = (p_val == check_product)
    
    print("\nCalculated Values:")
    print("  P(" + str(n) + ", " + str(r) + ") = " + format_large_number(p_val))
    print("  C(" + str(n) + ", " + str(r) + ") = " + format_large_number(c_val))
    print("  r! = " + str(r) + "! = " + format_large_number(r_fact))
    print("  C(n, r) * r! = " + format_large_number(check_product))
    print("  Identity Verification: " + ("VERIFIED [P = C * r!]" if is_valid else "FAILED"))
    
    # For small n and r, explicitly show sample letter orderings
    if n <= 6 and r <= 4 and r > 0:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:r]
        sample_group = list(alphabet)
        print("\nDemonstration with sample group " + str(sample_group) + ":")
        arrangements, _, _ = combinatorics.list_letter_permutations(r, r)
        rendered_orderings = []
        for tup in arrangements:
            rendered_orderings.append("".join(tup))
        print("  All " + str(r_fact) + " distinct orderings counting as 1 combination group:")
        print("  " + ", ".join(rendered_orderings))
    
    res_str = "P=" + format_large_number(p_val) + ", C=" + format_large_number(c_val)
    history_manager.save_history_record("Comparison", "n=" + str(n) + ", r=" + str(r), res_str)
    prompt_and_show_visual(visualizer.plot_comparison, n, r)


def handle_permutations_with_repetition():
    print("\n--- 5. PERMUTATIONS WITH REPETITION (n^r) ---")
    print("Definition: Number of sequences of length r formed from n choices with replacement.")
    print("Formula: n^r   [r can be greater than n; order matters]")
    n = get_integer_input("Enter number of choices n (0 <= n <= 1000): ", 0, 1000)
    r = get_integer_input("Enter sequence length r (0 <= r <= 1000): ", 0, 1000)
    
    result = combinatorics.permutations_with_repetition(n, r)
    display_res = format_large_number(result)
    
    print("\nResult:")
    print("  " + str(n) + "^" + str(r) + " = " + display_res)
    print("  Difference from ordinary permutations: Each of the " + str(r) + " positions has the full")
    print("  choice of " + str(n) + " elements, because elements can be reused repeatedly.")
    if n == 0 and r == 0:
        print("  Note on 0^0: By convention, there is exactly 1 empty sequence of length 0.")
    
    history_manager.save_history_record("Permutations with Repetition", "n=" + str(n) + ", r=" + str(r), display_res)
    prompt_and_show_visual(visualizer.plot_perm_with_repetition, n, r)


def handle_combinations_with_repetition():
    print("\n--- 6. COMBINATIONS WITH REPETITION (Multichoose) ---")
    print("Definition: Number of un-ordered selections of r items from n item types with replacement.")
    print("Formula: C(n + r - 1, r)   [Stars and Bars theorem; r can be greater than n]")
    n = get_integer_input("Enter number of item types n (0 <= n <= 1000): ", 0, 1000)
    r = get_integer_input("Enter items to select r (0 <= r <= 1000): ", 0, 1000)
    
    result = combinatorics.combinations_with_repetition(n, r)
    display_res = format_large_number(result)
    
    print("\nResult:")
    if n == 0:
        print("  For n = 0 types: result = " + str(result))
    else:
        equiv_n = n + r - 1
        print("  C(" + str(n) + " + " + str(r) + " - 1, " + str(r) + ") = C(" + str(equiv_n) + ", " + str(r) + ") = " + display_res)
    print("  Difference from ordinary combinations: Items are not consumed upon selection.")
    print("  For example, choosing 3 scoops from 5 ice-cream flavors = C(5 + 3 - 1, 3) = C(7, 3) = 35.")
    
    history_manager.save_history_record("Combinations with Repetition", "n=" + str(n) + ", r=" + str(r), display_res)
    prompt_and_show_visual(visualizer.plot_comb_with_repetition, n, r)


def handle_multiset_arrangements():
    print("\n--- 7. ARRANGEMENTS OF REPEATED OBJECTS (Multiset) ---")
    print("Formula: n! / (n1! * n2! * ... * nk!) where n = n1 + n2 + ... + nk.")
    print("Note: Input is case-sensitive and accepts up to 50 alphanumeric characters.")
    text = get_string_input("Enter alphanumeric word (max 50 chars): ", max_len=50, allow_alnum_only=True)
    
    total_count, freq = combinatorics.multiset_arrangements_count(text)
    display_res = format_large_number(total_count)
    
    print("\nCharacter Frequencies (Stored in dictionary):")
    denom_parts = []
    for ch in sorted(freq.keys()):
        print("  '" + ch + "': " + str(freq[ch]))
        denom_parts.append(str(freq[ch]) + "!")
    
    n_len = len(text)
    denom_str = " * ".join(denom_parts) if denom_parts else "1"
    print("\nFormula Substitution:")
    print("  Total Permutations = " + str(n_len) + "! / (" + denom_str + ")")
    print("  Result = " + display_res)
    print("  Example check: 'MISSISSIPPI' has 11 letters with 1 M, 4 I, 4 S, 2 P = 11!/(1!*4!*4!*2!) = 34650.")
    
    history_manager.save_history_record("Multiset Arrangements", "text='" + text + "'", display_res)
    prompt_and_show_visual(visualizer.plot_multiset, text)


def handle_listing():
    print("\n--- 8. LIST ARRANGEMENTS / GROUPS (Small Inputs Only) ---")
    print("Sub-menu:")
    print("  1. List permutations P(n, r) of uppercase letters (n <= 8)")
    print("  2. List combinations C(n, r) of uppercase letters (n <= 8)")
    print("  3. List distinct multiset permutations of a word (length <= 8)")
    sub_choice = get_integer_input("Select sub-option (1-3): ", 1, 3)
    
    if sub_choice == 1:
        n = get_integer_input("Enter n (1 <= n <= 8): ", 1, 8)
        r = get_integer_input("Enter r (1 <= r <= " + str(n) + "): ", 1, n)
        items, theo, is_match = combinatorics.list_letter_permutations(n, r)
        label = "P(" + str(n) + "," + str(r) + ")"
    elif sub_choice == 2:
        n = get_integer_input("Enter n (1 <= n <= 8): ", 1, 8)
        r = get_integer_input("Enter r (1 <= r <= " + str(n) + "): ", 1, n)
        items, theo, is_match = combinatorics.list_letter_combinations(n, r)
        label = "C(" + str(n) + "," + str(r) + ")"
    else:
        word = get_string_input("Enter word (max 8 characters): ", max_len=8, allow_alnum_only=True)
        items, theo, is_match = combinatorics.list_multiset_permutations(word)
        label = "Multiset '" + word + "'"
    
    total_found = len(items)
    print("\nListing Results for " + label + ":")
    print("  Theoretical count from formula: " + str(theo))
    print("  Generated count from listing:   " + str(total_found))
    print("  Verification:                   " + ("MATCH" if is_match else "MISMATCH"))
    
    limit_display = 500
    display_items = items[:limit_display]
    
    print("\n  Arrangements / Groups (showing up to " + str(limit_display) + "):")
    formatted_rows = []
    for tup in display_items:
        formatted_rows.append("".join(tup))
    
    # Print in clean columns of 10 items per line
    for i in range(0, len(formatted_rows), 10):
        print("  " + "  ".join(formatted_rows[i:i + 10]))
    
    if total_found > limit_display:
        print("\n  [Truncated] " + str(total_found - limit_display) + " items were not shown to keep output clean.")
    
    history_manager.save_history_record("Listing (" + label + ")", "count=" + str(total_found), "MATCH" if is_match else "MISMATCH")
    if sub_choice == 1:
        prompt_and_show_visual(visualizer.plot_listing, "perm", n, r, "")
    elif sub_choice == 2:
        prompt_and_show_visual(visualizer.plot_listing, "comb", n, r, "")
    else:
        prompt_and_show_visual(visualizer.plot_listing, "multiset", 0, 0, word)


def handle_binomial_identities():
    print("\n--- 9. BINOMIAL COEFFICIENT IDENTITIES ---")
    print("Verifies: (1) Symmetry C(n,r) = C(n,n-r), (2) Pascal's Identity, (3) Row Sum = 2^n.")
    n = get_integer_input("Enter n (0 <= n <= 1000): ", 0, 1000)
    r = get_integer_input("Enter r (0 <= r <= " + str(n) + "): ", 0, n)
    
    rep = combinatorics.verify_binomial_identities(n, r)
    
    print("\nResults for n = " + str(n) + ", r = " + str(r) + ":")
    print("  Calculated C(" + str(n) + ", " + str(r) + ") = " + format_large_number(rep["c_nr"]))
    
    # 1. Symmetry
    sym_status = "VERIFIED" if rep["symmetry_verified"] else "FAILED"
    print("\n1. Symmetry Identity: C(n, r) = C(n, n - r)")
    print("   C(" + str(n) + ", " + str(r) + ") = " + format_large_number(rep["c_nr"]))
    print("   C(" + str(n) + ", " + str(n - r) + ") = " + format_large_number(rep["c_sym"]))
    print("   Status: " + sym_status)
    
    # 2. Pascal's identity
    print("\n2. Pascal's Additive Identity: C(n, r) = C(n - 1, r - 1) + C(n - 1, r)")
    if rep["pascal_applicable"]:
        pascal_status = "VERIFIED" if rep["pascal_verified"] else "FAILED"
        print("   " + rep["pascal_note"])
        print("   Status: " + pascal_status)
    else:
        print("   " + rep["pascal_note"])
        print("   Status: NOT APPLICABLE (Boundary element r = 0 or r = n)")
    
    # 3. Row sum
    row_sum_status = "VERIFIED" if rep["row_sum_verified"] else "FAILED"
    print("\n3. Row Sum Identity: Sum_{k=0}^{n} C(n, k) = 2^n")
    print("   Sum of row " + str(n) + " entries = " + format_large_number(rep["row_sum_value"]))
    print("   Theoretical 2^" + str(n) + "          = " + format_large_number(rep["power_of_two"]))
    print("   Status: " + row_sum_status)
    
    history_manager.save_history_record("Binomial Identities", "n=" + str(n) + ", r=" + str(r), "All verified")
    prompt_and_show_visual(visualizer.plot_binomial_identities, n, r)


def handle_pascal_triangle():
    print("\n--- 10. PASCAL'S TRIANGLE ---")
    print("Row numbering starts at row 0 (Row 0 has 1 element: [1]).")
    rows = get_integer_input("Enter number of rows to display (1 to 15): ", 1, 15)
    
    triangle = combinatorics.generate_pascal_triangle(rows)
    
    # Determine maximum number width for clean centered alignment
    max_num = max(max(row) for row in triangle)
    col_width = len(str(max_num)) + 2
    
    print("\nPascal's Triangle (Rows 0 to " + str(rows - 1) + "):")
    for r_idx in range(len(triangle)):
        row = triangle[r_idx]
        row_str = " ".join([str(val).center(col_width) for val in row])
        row_sum = sum(row)
        line = row_str.center(rows * col_width)
        print("Row " + str(r_idx).rjust(2) + ": " + line + "  (Sum: " + str(row_sum) + " = 2^" + str(r_idx) + ")")
    
    print("\nMathematical Properties:")
    print("  - The first and last numbers in every row are always 1 because C(n, 0) = C(n, n) = 1.")
    print("  - Every interior entry is the exact sum of the two numbers immediately above it (Pascal's rule).")
    print("  - Row 5 values: 1 5 10 10 5 1 with total row sum 32 (= 2^5).")
    
    history_manager.save_history_record("Pascal's Triangle", "rows=" + str(rows), "Generated " + str(rows) + " rows")
    prompt_and_show_visual(visualizer.plot_pascal_triangle, rows)


def handle_recurrence():
    print("\n--- 11. RECURRENCE RELATION ANALYZER ---")
    print("Sub-menu:")
    print("  1. Fibonacci Sequence: F(0)=0, F(1)=1, F(n) = F(n-1) + F(n-2)")
    print("  2. Factorial Recurrence: a(0)=1, a(n) = n * a(n-1)")
    print("  3. Custom Linear Recurrence of Order k (1 <= k <= 5)")
    choice = get_integer_input("Select recurrence type (1-3): ", 1, 3)
    
    if choice == 1:
        terms = get_integer_input("Enter number of terms to generate (1 to 50): ", 1, 50)
        seq = recurrence.fibonacci_sequence(terms)
        rec_name = "Fibonacci"
        details = "F(0)=0, F(1)=1; F(n) = F(n-1) + F(n-2)"
    elif choice == 2:
        terms = get_integer_input("Enter number of terms to generate (1 to 50): ", 1, 50)
        seq = recurrence.factorial_recurrence(terms)
        rec_name = "Factorial Recurrence"
        details = "a(0)=1; a(n) = n * a(n-1)"
    else:
        k = get_integer_input("Enter recurrence order k (1 to 5): ", 1, 5)
        print("\nEnter " + str(k) + " integer coefficients c1, c2, ..., ck for:")
        print("  a(n) = c1*a(n-1) + c2*a(n-2) + ... + ck*a(n-k)")
        print("Note: The last coefficient c" + str(k) + " must be non-zero so the order truly is " + str(k) + ".")
        coeffs = []
        for i in range(1, k + 1):
            if i == k:
                # Must be non-zero
                while True:
                    c_val = get_integer_input("  c" + str(i) + " (non-zero integer, |c| <= 1000): ", -1000, 1000)
                    if c_val != 0:
                        coeffs.append(c_val)
                        break
                    print("  [Error] Trailing coefficient c" + str(k) + " cannot be 0.")
            else:
                c_val = get_integer_input("  c" + str(i) + " (integer, |c| <= 1000): ", -1000, 1000)
                coeffs.append(c_val)
        
        print("\nEnter " + str(k) + " integer initial conditions a(0), a(1), ..., a(" + str(k - 1) + "):")
        init_vals_list = []
        for i in range(k):
            val = get_integer_input("  a(" + str(i) + ") (integer, |val| <= 1000): ", -1000, 1000)
            init_vals_list.append(val)
        init_vals = tuple(init_vals_list)
        
        terms = get_integer_input("Enter number of terms to generate (1 to 50): ", 1, 50)
        seq = recurrence.custom_linear_recurrence(k, coeffs, init_vals, terms)
        rec_name = "Custom Order " + str(k)
        details = "Coeffs=" + str(coeffs) + ", Init=" + str(init_vals)
    
    print("\nGenerated Sequence for " + rec_name + ":")
    print("  Relation / Parameters: " + details)
    print("  Terms generated (0 to " + str(len(seq) - 1) + "):")
    for idx, val in enumerate(seq):
        print("    a(" + str(idx).rjust(2) + ") = " + format_large_number(val))
    
    print("\nImportant Distinction:")
    print("  Generating numerical sequence terms iteratively is NOT the same as determining a closed-form")
    print("  symbolic solution (which expresses a(n) as a direct function of n without previous terms).")
    
    history_manager.save_history_record(rec_name, details + ", terms=" + str(terms), "Generated " + str(len(seq)) + " terms")
    rec_type_key = "fibonacci" if choice == 1 else ("factorial" if choice == 2 else "custom")
    prompt_and_show_visual(visualizer.plot_recurrence, rec_type_key, seq, rec_name)


def handle_binomial_expansion():
    print("\n--- 12. BINOMIAL THEOREM EXPANSION ---")
    print("Formula: (a*x + b*y)^n = Sum_{k=0}^{n} C(n, k) * a^(n-k) * b^k * x^(n-k) * y^k")
    n = get_integer_input("Enter exponent n (0 <= n <= 20): ", 0, 20)
    
    print("Custom coefficients (a*x + b*y)^n [Enter a=1, b=1 for standard (x+y)^n]:")
    a = get_integer_input("  Enter integer a (-10 <= a <= 10): ", -10, 10)
    b = get_integer_input("  Enter integer b (-10 <= b <= 10): ", -10, 10)
    
    terms = combinatorics.binomial_expansion_terms(n, a, b)
    formatted_expansion = combinatorics.format_binomial_expansion(terms)
    
    input_repr = "(" + (str(a) if a != 1 else "") + "x + " + (str(b) if b != 1 else "") + "y)^" + str(n)
    print("\nResult:")
    print("  " + input_repr + " =")
    print("  " + formatted_expansion)
    
    # Optional SymPy verification
    if sympy_tools.is_sympy_available():
        _, sym_expanded, note = sympy_tools.sympy_verify_expansion(n, a, b, terms)
        print("\nSymPy Formal Check:")
        print("  " + note)
        print("  SymPy output: " + sym_expanded)
    
    history_manager.save_history_record("Binomial Expansion", "n=" + str(n) + ", a=" + str(a) + ", b=" + str(b), formatted_expansion)
    prompt_and_show_visual(visualizer.plot_binomial_expansion, n, a, b)


def handle_sympy_verification():
    print("\n--- 13. SYMPY VERIFICATION (OPTIONAL FORMAL MATH CHECK) ---")
    if not sympy_tools.is_sympy_available():
        print(sympy_tools.get_install_instructions())
        print("All combinatorial, recurrence, and expansion features continue working independently.")
        return
    
    print("SymPy Version Detected: " + sympy_tools.get_sympy_version())
    print("Sub-menu:")
    print("  1. Formal factorial verification")
    print("  2. Formal combination C(n, r) verification")
    print("  3. Formal binomial expansion verification")
    print("  4. Symbolic recurrence closed-form solver (rsolve)")
    sub_choice = get_integer_input("Select verification task (1-4): ", 1, 4)
    
    if sub_choice == 1:
        n = get_integer_input("Enter n (0 <= n <= 100): ", 0, 100)
        my_val = combinatorics.factorial(n)
        is_match, sym_val, note = sympy_tools.sympy_verify_factorial(n, my_val)
        print("  " + note)
    elif sub_choice == 2:
        n = get_integer_input("Enter n (0 <= n <= 100): ", 0, 100)
        r = get_integer_input("Enter r (0 <= r <= " + str(n) + "): ", 0, n)
        my_val = combinatorics.combinations(n, r)
        is_match, sym_val, note = sympy_tools.sympy_verify_combination(n, r, my_val)
        print("  " + note)
    elif sub_choice == 3:
        n = get_integer_input("Enter n (0 <= n <= 15): ", 0, 15)
        a = get_integer_input("Enter a (-10 <= a <= 10): ", -10, 10)
        b = get_integer_input("Enter b (-10 <= b <= 10): ", -10, 10)
        terms = combinatorics.binomial_expansion_terms(n, a, b)
        is_match, sym_expr, note = sympy_tools.sympy_verify_expansion(n, a, b, terms)
        print("  " + note)
        print("  Canonical SymPy expression: " + sym_expr)
    else:
        print("\nSymbolic Closed-Form Solver (rsolve):")
        print("  1. Fibonacci Sequence: F(n) = F(n-1) + F(n-2), F(0)=0, F(1)=1")
        print("  2. Custom Order 1: a(n) = c1 * a(n-1)")
        print("  3. Custom Order 2: a(n) = c1 * a(n-1) + c2 * a(n-2)")
        sub_rec = get_integer_input("Select recurrence to solve (1-3): ", 1, 3)
        if sub_rec == 1:
            my_seq = recurrence.fibonacci_sequence(10)
            ok, sol_str, checks, note = sympy_tools.sympy_closed_form_recurrence("fibonacci", 2, [1, 1], (0, 1), my_seq)
        elif sub_rec == 2:
            c1 = get_integer_input("Enter c1 (non-zero integer): ", -1000, 1000)
            a0 = get_integer_input("Enter a(0): ", -1000, 1000)
            my_seq = recurrence.custom_linear_recurrence(1, [c1], (a0,), 10)
            ok, sol_str, checks, note = sympy_tools.sympy_closed_form_recurrence("custom", 1, [c1], (a0,), my_seq)
        else:
            c1 = get_integer_input("Enter c1: ", -1000, 1000)
            c2 = get_integer_input("Enter c2 (non-zero integer): ", -1000, 1000)
            a0 = get_integer_input("Enter a(0): ", -1000, 1000)
            a1 = get_integer_input("Enter a(1): ", -1000, 1000)
            my_seq = recurrence.custom_linear_recurrence(2, [c1, c2], (a0, a1), 10)
            ok, sol_str, checks, note = sympy_tools.sympy_closed_form_recurrence("custom", 2, [c1, c2], (a0, a1), my_seq)
        
        if ok:
            print("\nClosed-form solution a(n):")
            print("  " + sol_str)
            print("Term-by-term symbolic verification (first 10 terms):")
            for chk in checks:
                status_str = "MATCH" if chk["matched"] else "MISMATCH"
                print("  n=" + str(chk["n"]) + ": generated=" + str(chk["my_term"]) + ", closed_form=" + str(chk["sympy_val"]) + " [" + status_str + "]")
            print("  " + note)
        else:
            print("  [Could not solve] " + note)


def handle_history():
    print("\n--- 14. CALCULATION HISTORY ---")
    print("Sub-menu:")
    print("  1. View all recorded calculations")
    print("  2. Search history by operation name or parameter")
    sub_choice = get_integer_input("Select history option (1-2): ", 1, 2)
    
    if sub_choice == 1:
        records, skipped = history_manager.read_history_records()
        header = "ALL HISTORY RECORDS"
    else:
        query = get_string_input("Enter search keyword (e.g., 'Factorial', 'MISSISSIPPI'): ", max_len=50, allow_alnum_only=False)
        records, total_count, skipped = history_manager.search_history_records(query)
        header = "HISTORY SEARCH RESULTS FOR '" + query + "'"
    
    print("\n" + "=" * 80)
    print(header.center(80))
    print("=" * 80)
    if not records:
        print("No calculation records found.")
    else:
        print("Timestamp           | Operation                 | Inputs               | Result")
        print("-" * 80)
        for r in records:
            ts = r["timestamp"].ljust(19)
            op = r["operation"][:25].ljust(25)
            inp = r["inputs"][:20].ljust(20)
            res = r["result"][:30]
            print(ts + " | " + op + " | " + inp + " | " + res)
    
    if skipped > 0:
        print("\nNote: " + str(skipped) + " malformed lines were safely skipped.")
    print("=" * 80)


def handle_self_test():
    print("\n--- 15. RUN AUTOMATED SELF-TEST SUITE ---")
    print("Executing internal plain-function test suite...\n")
    summary = tests.run_all_tests()
    history_manager.save_history_record("Self-Test", "Total=" + str(summary["total"]), "Passed=" + str(summary["passed"]) + "/" + str(summary["total"]))


def handle_visual_gallery():
    print("\n--- 16. DEMO VISUAL EXPLANATION GALLERY ---")
    print("Generating all 12 visual explanation charts into the plots/ folder...")
    if not visualizer.is_visualizer_available():
        print("  [Visualizer Note] Matplotlib is not installed. To enable visual charts, run: pip install matplotlib")
        return
    
    plots_list = visualizer.generate_all_demo_plots()
    print("\nGenerated " + str(len(plots_list)) + " visual charts:")
    for idx, item in enumerate(plots_list, 1):
        desc, path = item
        print("  " + str(idx).rjust(2) + ". " + desc.ljust(45) + " -> " + path)
    
    print("\nOptions:")
    print("  Enter chart number (1-12) to open that chart in default image viewer")
    print("  Enter 0 to return to main menu")
    choice = get_integer_input("Choice (0-12): ", 0, len(plots_list))
    if choice > 0:
        target_path = plots_list[choice - 1][1]
        try:
            if hasattr(os, "startfile"):
                os.startfile(target_path)
            else:
                import subprocess
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.run([opener, target_path], check=False)
            print("  Opened: " + target_path)
        except Exception:
            print("  [Viewer Note] File saved at: " + target_path)


# =============================================================================
# MAIN INTERACTIVE LOOP
# =============================================================================

def print_menu():
    print("\n" + "=" * 70)
    print("   COMBINATORIAL COUNTING AND PERMUTATION ANALYZER")
    print("=" * 70)
    print(" 1. Factorial")
    print(" 2. Permutations P(n, r)")
    print(" 3. Combinations C(n, r)")
    print(" 4. Permutation vs Combination comparison")
    print(" 5. Permutations with repetition")
    print(" 6. Combinations with repetition")
    print(" 7. Arrangements of repeated objects (multiset)")
    print(" 8. List arrangements / groups (small inputs only)")
    print(" 9. Binomial coefficient identities (symmetry, Pascal, row sum)")
    print("10. Pascal's triangle")
    print("11. Recurrence relation analyzer")
    print("12. Binomial theorem expansion")
    print("13. SymPy verification (optional formal check)")
    print("14. History (view all / search)")
    print("15. Run self-test (PASS/FAIL list)")
    print("16. Visual gallery (generate all 12 demo plots)")
    print(" 0. Exit")
    print("=" * 70)


def main():
    """Main program coordination loop."""
    print("=" * 70)
    print("Welcome to Combinatorial Counting and Permutation Analyzer")
    print("Academic Lab Submission Project (Python 3.8+)")
    print("=" * 70)
    
    # Menu routing table (mapping choice to handler function)
    menu_actions = {
        1: handle_factorial,
        2: handle_permutations,
        3: handle_combinations,
        4: handle_comparison,
        5: handle_permutations_with_repetition,
        6: handle_combinations_with_repetition,
        7: handle_multiset_arrangements,
        8: handle_listing,
        9: handle_binomial_identities,
        10: handle_pascal_triangle,
        11: handle_recurrence,
        12: handle_binomial_expansion,
        13: handle_sympy_verification,
        14: handle_history,
        15: handle_self_test,
        16: handle_visual_gallery
    }
    
    while True:
        print_menu()
        choice = get_integer_input("Select an option (0-16): ", 0, 16)
        
        if choice == 0:
            print("\nThank you for using Combinatorial Counting and Permutation Analyzer. Goodbye!")
            break
        
        action = menu_actions.get(choice)
        if action:
            try:
                action()
            except Exception as e:
                print("\n[Unexpected Error] An issue occurred during calculation: " + str(e))
        else:
            print("Invalid selection. Please choose an integer between 0 and 16.")


if __name__ == "__main__":
    main()
