# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Terminal version of the app (python main.py).
# Each handle_* function asks for its inputs, prints the result with a short explanation,
# saves it to history and offers to draw the chart. The maths lives in combinatorics.py
# and recurrence.py; this file only deals with input and output.

import os
import sys
import subprocess

import combinatorics
import recurrence
import sympy_tools
import history_manager
import visualizer

MAX_N = 1000


def read_line(prompt):
    # Ctrl+C or Ctrl+D at any prompt exits cleanly instead of printing a traceback.
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nGoodbye!")
        sys.exit(0)


def ask_int(prompt, low, high):
    # Keeps asking until the user types a whole number in [low, high].
    while True:
        raw = read_line(f"{prompt} ({low} to {high}): ")
        try:
            value = int(raw)
        except ValueError:
            print(f"  [Error] '{raw}' is not a whole number. Please try again.")
            continue
        if low <= value <= high:
            return value
        print(f"  [Error] Please enter a value between {low} and {high}.")


def ask_word(prompt, max_len, alnum_only=True):
    while True:
        raw = read_line(f"{prompt} (max {max_len} characters): ")
        if not raw:
            print("  [Error] Input cannot be empty.")
        elif len(raw) > max_len:
            print(f"  [Error] Maximum length is {max_len} characters.")
        elif alnum_only and not raw.isalnum():
            print("  [Error] Only letters and digits are allowed.")
        else:
            return raw


def ask_yes(prompt):
    return ask_int(prompt + " 1 = yes, 0 = no", 0, 1) == 1


def ask_n_r(r_limited=True):
    # r <= n for ordinary P and C; the "with repetition" variants allow r > n.
    n = ask_int("Enter n", 0, MAX_N)
    r = ask_int("Enter r", 0, n if r_limited else MAX_N)
    return n, r


def short(value):
    # Shortens very long numbers (1000! has 2,568 digits) to "first 20...last 10 (N digits)".
    s = str(value)
    return s if len(s) <= 60 else f"{s[:20]}...{s[-10:]} ({len(s)} digits)"


def open_file(path):
    # Opens a saved chart in the default image viewer (Windows, macOS or Linux).
    # Failing to open it is harmless because the path has already been printed.
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", path], check=False)
    except OSError:
        pass


def finish(operation, inputs, result, plot_func, *plot_args):
    # Common ending of every calculation: save it to history, then offer the chart.
    history_manager.save_history_record(operation, inputs, result)
    if not visualizer.MATPLOTLIB_AVAILABLE:
        print("  (Install matplotlib to see visual explanations.)")
        return
    if ask_yes("\nShow visual explanation?"):
        path = plot_func(*plot_args)
        print("  Saved plot to " + path)
        open_file(path)


def handle_factorial():
    print("\nFactorial: n! = n * (n - 1) * ... * 1, with 0! = 1")
    n = ask_int("Enter n", 0, MAX_N)
    value = combinatorics.factorial(n)
    result = short(value)
    print(f"\n  {n}! = {result}")
    if sympy_tools.SYMPY_AVAILABLE:
        print("  SymPy check: " + sympy_tools.verify_factorial(n, value)[2])
    finish("Factorial", f"n={n}", result, visualizer.plot_factorial, n)


def handle_permutations():
    print("\nPermutations: P(n, r) = n! / (n - r)!   (order matters)")
    n, r = ask_n_r()
    result = short(combinatorics.permutations(n, r))
    print(f"\n  P({n}, {r}) = {n}! / {n - r}! = {result}")
    finish("Permutations", f"n={n}, r={r}", result, visualizer.plot_permutations, n, r)


def handle_combinations():
    print("\nCombinations: C(n, r) = n! / (r! * (n - r)!)   (order does not matter)")
    n, r = ask_n_r()
    value = combinatorics.combinations(n, r)
    result = short(value)
    print(f"\n  C({n}, {r}) = {n}! / ({r}! * {n - r}!) = {result}")
    print("  We divide by r! because the r! orderings of each group count as one selection.")
    if sympy_tools.SYMPY_AVAILABLE:
        print("  SymPy check: " + sympy_tools.verify_combination(n, r, value)[2])
    finish("Combinations", f"n={n}, r={r}", result, visualizer.plot_combinations, n, r)


def handle_comparison():
    print("\nComparison: P(n, r) = C(n, r) * r!")
    n, r = ask_n_r()
    p, c, rf = combinatorics.permutations(n, r), combinatorics.combinations(n, r), combinatorics.factorial(r)
    print(f"\n  P({n}, {r}) = {short(p)}")
    print(f"  C({n}, {r}) = {short(c)}")
    print(f"  {r}! = {short(rf)}")
    print("  P = C * r! : " + ("VERIFIED" if p == c * rf else "FAILED"))
    if 0 < r <= 4 and n <= 6:
        orderings = ["".join(t) for t in combinatorics.list_letter_permutations(r, r)[0]]
        print(f"  The {rf} orderings of one group: " + ", ".join(orderings))
    finish("Comparison", f"n={n}, r={r}", f"P={short(p)}, C={short(c)}", visualizer.plot_comparison, n, r)


def handle_permutations_with_repetition():
    print("\nPermutations with repetition: n^r   (items can be reused)")
    n, r = ask_n_r(r_limited=False)
    result = short(combinatorics.permutations_with_repetition(n, r))
    print(f"\n  {n}^{r} = {result}")
    finish("Permutations with Repetition", f"n={n}, r={r}", result, visualizer.plot_perm_with_repetition, n, r)


def handle_combinations_with_repetition():
    print("\nCombinations with repetition: C(n + r - 1, r)   (stars and bars)")
    n, r = ask_n_r(r_limited=False)
    result = short(combinatorics.combinations_with_repetition(n, r))
    print(f"\n  C({n} + {r} - 1, {r}) = {result}")
    finish("Combinations with Repetition", f"n={n}, r={r}", result, visualizer.plot_comb_with_repetition, n, r)


def handle_multiset():
    print("\nArrangements of a word with repeated letters: n! / (n1! * n2! * ... * nk!)")
    text = ask_word("Enter a word", 50)
    count, freq = combinatorics.multiset_arrangements_count(text)
    result = short(count)
    for ch in sorted(freq):
        print(f"  '{ch}': {freq[ch]}")
    denominator = " * ".join(f"{freq[ch]}!" for ch in sorted(freq))
    print(f"\n  {len(text)}! / ({denominator}) = {result}")
    finish("Multiset Arrangements", f"word='{text}'", result, visualizer.plot_multiset, text)


def handle_listing():
    print("\n  1. List permutations of letters\n  2. List combinations of letters\n  3. List arrangements of a word")
    choice = ask_int("Choose", 1, 3)
    if choice == 3:
        word = ask_word("Enter a word", 8)
        items, expected, ok = combinatorics.list_multiset_permutations(word)
        mode, n, r, label = "multiset", 0, 0, f"word '{word}'"
    else:
        n = ask_int("Enter n", 1, 8)
        r = ask_int("Enter r", 1, n)
        word = ""
        if choice == 1:
            items, expected, ok = combinatorics.list_letter_permutations(n, r)
            mode, label = "perm", f"P({n}, {r})"
        else:
            items, expected, ok = combinatorics.list_letter_combinations(n, r)
            mode, label = "comb", f"C({n}, {r})"

    status = "MATCH" if ok else "MISMATCH"
    print(f"\n  {label}: formula = {expected}, listed = {len(items)}, unique = {len(set(items))} -> {status}")
    shown = ["".join(t) for t in items[:500]]
    for i in range(0, len(shown), 10):
        print("  " + "  ".join(shown[i:i + 10]))
    if len(items) > 500:
        print(f"  ... {len(items) - 500} more not shown")
    finish(f"Listing {label}", f"count={len(items)}", status, visualizer.plot_listing, mode, n, r, word)


def handle_binomial_identities():
    print("\nBinomial identities: symmetry, Pascal's rule, and row sum = 2^n")
    n, r = ask_n_r()
    rep = combinatorics.verify_binomial_identities(n, r)
    status = {True: "VERIFIED", False: "FAILED", None: "NOT APPLICABLE"}
    print(f"\n  1. C({n}, {r}) = C({n}, {n - r}) = {short(rep['c_nr'])}: {status[rep['symmetry_verified']]}")
    print(f"  2. {rep['pascal_note']}: {status[rep['pascal_verified']]}")
    print(f"  3. Sum of row {n} = {short(rep['row_sum_value'])} = 2^{n}: {status[rep['row_sum_verified']]}")
    finish("Binomial Identities", f"n={n}, r={r}", "All verified", visualizer.plot_binomial_identities, n, r)


def handle_pascal_triangle():
    rows = ask_int("Enter number of rows", 1, 15)
    triangle = combinatorics.generate_pascal_triangle(rows)
    width = len(str(max(triangle[-1]))) + 2
    print()
    for i, row in enumerate(triangle):
        line = "".join(str(v).center(width) for v in row).center(rows * width)
        print(f"Row {i:2}: {line}  (sum = 2^{i} = {sum(row)})")
    finish("Pascal's Triangle", f"rows={rows}", f"Generated {rows} rows", visualizer.plot_pascal_triangle, rows)


def handle_recurrence():
    print("\n  1. Fibonacci: F(n) = F(n-1) + F(n-2)\n  2. Factorial: a(n) = n * a(n-1)\n  3. Custom: a(n) = c1*a(n-1) + ... + ck*a(n-k)")
    choice = ask_int("Choose", 1, 3)
    if choice == 1:
        terms = ask_int("Number of terms", 1, recurrence.MAX_TERMS)
        seq, name, kind = recurrence.fibonacci_sequence(terms), "Fibonacci", "fibonacci"
    elif choice == 2:
        terms = ask_int("Number of terms", 1, recurrence.MAX_TERMS)
        seq, name, kind = recurrence.factorial_recurrence(terms), "Factorial Recurrence", "factorial"
    else:
        k = ask_int("Order k", 1, 5)
        coeffs = [ask_int(f"  c{i}", -1000, 1000) for i in range(1, k)]
        # The last coefficient is asked separately because 0 would reduce the order below k.
        while True:
            last = ask_int(f"  c{k} (must not be 0)", -1000, 1000)
            if last != 0:
                break
        coeffs.append(last)
        inits = tuple(ask_int(f"  a({i})", -1000, 1000) for i in range(k))
        terms = ask_int("Number of terms", 1, recurrence.MAX_TERMS)
        seq, name, kind = recurrence.custom_linear_recurrence(k, coeffs, inits, terms), f"Custom order {k} {coeffs}", "custom"

    print(f"\n  {name}:")
    for i, value in enumerate(seq):
        print(f"    a({i:2}) = {short(value)}")
    finish(name, f"terms={terms}", f"Generated {len(seq)} terms", visualizer.plot_recurrence, kind, seq, name)


def handle_binomial_expansion():
    print("\nBinomial expansion of (a*x + b*y)^n   (use a = 1, b = 1 for (x + y)^n)")
    n = ask_int("Enter n", 0, 20)
    a = ask_int("Enter a", -10, 10)
    b = ask_int("Enter b", -10, 10)
    terms = combinatorics.binomial_expansion_terms(n, a, b)
    label, result = combinatorics.binomial_label(n, a, b), combinatorics.format_binomial_expansion(terms)
    print(f"\n  {label} = {result}")
    if sympy_tools.SYMPY_AVAILABLE:
        print("  SymPy check: " + sympy_tools.verify_expansion(n, a, b, terms)[2])
    finish("Binomial Expansion", label, result, visualizer.plot_binomial_expansion, n, a, b)


def handle_derangements():
    print("\nDerangements: D(n) = (n - 1) * [D(n - 1) + D(n - 2)], D(0) = 1, D(1) = 0")
    n = ask_int("Enter n", 0, MAX_N)
    rep = combinatorics.derangements_report(n)
    result = short(rep["derangements"])
    print(f"\n  D({n}) = {result}")
    print(f"  n! = {short(rep['factorial'])}")
    print(f"  D(n) / n! = {rep['ratio']:.8f}   (1/e = {rep['limit']:.8f}, difference {rep['difference']:.2e})")
    first = combinatorics.derangements_list(min(max(n, 5), 9))
    print("  " + ", ".join(f"D({i})={v}" for i, v in enumerate(first)))
    finish("Derangements", f"n={n}", result, visualizer.plot_derangements, n)


def handle_circular_permutations():
    print("\nCircular permutations: P(n, r) / r   (divide by 2 more if flipping the circle is allowed)")
    n = ask_int("Enter n", 1, MAX_N)
    r = ask_int("Enter r", 1, n)
    reflections = ask_yes("Do mirror images count as the same?")
    result = short(combinatorics.circular_permutations(n, r, reflections))
    divisor = f"({r} * 2)" if reflections and r >= 3 else str(r)
    print(f"\n  P({n}, {r}) / {divisor} = {result}")
    finish("Circular Permutations", f"n={n}, r={r}, reflections={reflections}", result,
           visualizer.plot_circular_permutations, n, r, reflections)


def handle_sympy_verification():
    if not sympy_tools.SYMPY_AVAILABLE:
        print("\n" + sympy_tools.INSTALL_MESSAGE)
        return
    print(f"\nSymPy {sympy_tools.SYMPY_VERSION}")
    print("  1. Factorial\n  2. Combination C(n, r)\n  3. Binomial expansion\n  4. Recurrence closed form (rsolve)")
    choice = ask_int("Choose", 1, 4)
    if choice == 1:
        n = ask_int("Enter n", 0, 100)
        print("  " + sympy_tools.verify_factorial(n, combinatorics.factorial(n))[2])
    elif choice == 2:
        n = ask_int("Enter n", 0, 100)
        r = ask_int("Enter r", 0, n)
        print("  " + sympy_tools.verify_combination(n, r, combinatorics.combinations(n, r))[2])
    elif choice == 3:
        n = ask_int("Enter n", 0, 15)
        a = ask_int("Enter a", -10, 10)
        b = ask_int("Enter b", -10, 10)
        _, expanded, note = sympy_tools.verify_expansion(n, a, b, combinatorics.binomial_expansion_terms(n, a, b))
        print(f"  {note}\n  SymPy: {expanded}")
    else:
        order = ask_int("Order (1 = a(n) = c1*a(n-1), 2 = a(n) = c1*a(n-1) + c2*a(n-2))", 1, 2)
        coeffs = [ask_int(f"  c{i}", -1000, 1000) for i in range(1, order + 1)]
        if coeffs[-1] == 0:
            print("  [Error] The last coefficient must not be 0.")
            return
        inits = tuple(ask_int(f"  a({i})", -1000, 1000) for i in range(order))
        seq = recurrence.custom_linear_recurrence(order, coeffs, inits, 10)
        ok, solution, checks, note = sympy_tools.closed_form_recurrence(coeffs, inits, seq)
        if ok:
            print(f"\n  a(n) = {solution}")
            for c in checks:
                print(f"  n={c['n']}: generated={c['my_term']}, closed form={c['sympy_val']} [{'MATCH' if c['matched'] else 'MISMATCH'}]")
        print("  " + note)


def handle_history():
    print("\n  1. View all\n  2. Search\n  3. Clear")
    choice = ask_int("Choose", 1, 3)
    if choice == 3:
        if ask_yes("Clear all history?"):
            history_manager.clear_history()
            print("  History cleared.")
        return
    if choice == 1:
        records, skipped = history_manager.read_history_records()
    else:
        records, _, skipped = history_manager.search_history_records(ask_word("Search for", 50, alnum_only=False))
    print("\n" + "=" * 80)
    if not records:
        print("No records found.")
    for rec in records:
        print(f"{rec['timestamp']} | {rec['operation'][:25]:25} | {rec['inputs'][:20]:20} | {rec['result'][:30]}")
    if skipped:
        print(f"\n({skipped} malformed lines skipped)")
    print("=" * 80)


def handle_self_test():
    # Imported here rather than at the top so the menu starts without loading the tests.
    import tests
    summary = tests.run_all_tests()
    history_manager.save_history_record("Self-Test", f"Total={summary['total']}", f"Passed={summary['passed']}/{summary['total']}")


def handle_visual_gallery():
    if not visualizer.MATPLOTLIB_AVAILABLE:
        print("\nMatplotlib is not installed. To enable charts run: pip install matplotlib")
        return
    print("\nGenerating all demo charts into the plots/ folder...")
    plots = visualizer.generate_all_demo_plots()
    for i, (name, path) in enumerate(plots, 1):
        print(f"  {i:2}. {name:45} -> {path}")
    choice = ask_int("Open a chart (0 = back)", 0, len(plots))
    if choice:
        open_file(plots[choice - 1][1])


# Menu option number = position in this list + 1 (0 is Exit).
MENU = [
    ("Factorial", handle_factorial),
    ("Permutations P(n, r)", handle_permutations),
    ("Combinations C(n, r)", handle_combinations),
    ("Permutation vs Combination comparison", handle_comparison),
    ("Permutations with repetition", handle_permutations_with_repetition),
    ("Combinations with repetition", handle_combinations_with_repetition),
    ("Arrangements of repeated objects (multiset)", handle_multiset),
    ("List arrangements / groups (small inputs only)", handle_listing),
    ("Binomial coefficient identities", handle_binomial_identities),
    ("Pascal's triangle", handle_pascal_triangle),
    ("Recurrence relation analyzer", handle_recurrence),
    ("Binomial theorem expansion", handle_binomial_expansion),
    ("Derangements D(n)", handle_derangements),
    ("Circular permutations", handle_circular_permutations),
    ("SymPy verification (optional)", handle_sympy_verification),
    ("History (view / search / clear)", handle_history),
    ("Run self-test", handle_self_test),
    ("Visual gallery (generate all demo charts)", handle_visual_gallery),
]


def main():
    while True:
        print("\n" + "=" * 70)
        print("   COMBINATORIAL COUNTING AND PERMUTATION ANALYZER")
        print("=" * 70)
        for i, (name, _) in enumerate(MENU, 1):
            print(f"{i:2}. {name}")
        print(" 0. Exit")
        choice = ask_int("Select an option", 0, len(MENU))
        if choice == 0:
            print("\nGoodbye!")
            break
        # Any unexpected error is reported and the user returns to the menu.
        try:
            MENU[choice - 1][1]()
        except Exception as e:
            print(f"\n[Error] {e}")


if __name__ == "__main__":
    main()
