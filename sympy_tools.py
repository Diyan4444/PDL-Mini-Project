# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Optional second opinion from the SymPy library on our own results.
# SymPy is not required: without it every function returns an "install SymPy" message.
# Functions return (verified, sympy_value, note) so callers can print the note directly.

import combinatorics
import recurrence

try:
    import sympy
    SYMPY_AVAILABLE = True
    SYMPY_VERSION = sympy.__version__
except ImportError:
    SYMPY_AVAILABLE = False
    SYMPY_VERSION = "Not installed"

INSTALL_MESSAGE = "SymPy is not installed. To enable formal symbolic verification, run: pip install sympy"


def compare(label, sympy_value, my_value):
    if sympy_value == my_value:
        return True, sympy_value, f"SymPy {label} = {sympy_value} [VERIFIED MATCH]"
    return False, sympy_value, f"Mismatch: my result = {my_value}, SymPy = {sympy_value}"


def verify_factorial(n, my_value):
    if not SYMPY_AVAILABLE:
        return False, None, INSTALL_MESSAGE
    return compare(f"factorial({n})", int(sympy.factorial(n)), my_value)


def verify_combination(n, r, my_value):
    if not SYMPY_AVAILABLE:
        return False, None, INSTALL_MESSAGE
    return compare(f"binomial({n}, {r})", int(sympy.binomial(n, r)), my_value)


def verify_expansion(n, a, b, my_terms):
    if not SYMPY_AVAILABLE:
        return False, "", INSTALL_MESSAGE
    x, y = sympy.symbols("x y")
    expected = sympy.expand((a * x + b * y) ** n)
    mine = sum(coeff * x ** xp * y ** yp for coeff, xp, yp in my_terms)
    # The difference only expands to 0 if every coefficient matches.
    if sympy.expand(expected - mine) == 0:
        note = f"SymPy expand({combinatorics.binomial_label(n, a, b)}) matches my expansion. Difference = 0 [VERIFIED MATCH]"
        return True, str(expected), note
    return False, str(expected), "Expansion difference is not 0."


def closed_form_recurrence(coefficients, initial_values, my_terms):
    # Asks SymPy's rsolve for a direct formula for a(n) (for Fibonacci this is Binet's
    # formula), then substitutes n = 0..9 and compares with the terms we generated.
    if not SYMPY_AVAILABLE:
        return False, "", [], INSTALL_MESSAGE
    if len(coefficients) > 2:
        return False, "", [], "SymPy rsolve verification is limited to recurrences of order <= 2."
    n = sympy.symbols("n", integer=True)
    f = sympy.Function("f")
    # rsolve expects the recurrence as an expression equal to zero:
    # f(n) - c1*f(n-1) - c2*f(n-2), with initial values {f(0): a0, f(1): a1}.
    relation = f(n) - sum(c * f(n - i - 1) for i, c in enumerate(coefficients))
    solution = sympy.rsolve(relation, f(n), {f(i): v for i, v in enumerate(initial_values)})
    if solution is None:
        return False, "", [], "SymPy rsolve could not find a closed-form solution."
    checks = []
    for i, term in enumerate(my_terms[:10]):
        # simplify turns expressions with sqrt(5) back into an exact integer before comparing.
        value = sympy.simplify(solution.subs(n, i))
        checks.append({"n": i, "my_term": term, "sympy_val": str(value), "matched": value == term})
    if all(c["matched"] for c in checks):
        note = f"All {len(checks)} tested terms matched the SymPy closed form exactly [VERIFIED MATCH]"
    else:
        note = "Some terms differed from the SymPy closed form."
    return True, str(solution), checks, note


def run_all_symbolic_checks():
    # Fixed set of checks shown in the web page's SymPy section (via /api/sympy).
    if not SYMPY_AVAILABLE:
        return {"available": False, "version": SYMPY_VERSION, "message": INSTALL_MESSAGE, "results": []}
    ok_f, _, note_f = verify_factorial(10, combinatorics.factorial(10))
    ok_c, _, note_c = verify_combination(10, 4, combinatorics.combinations(10, 4))
    ok_e, expanded, note_e = verify_expansion(3, 2, -3, combinatorics.binomial_expansion_terms(3, 2, -3))
    ok_r, closed, checks, note_r = closed_form_recurrence([1, 1], (0, 1), recurrence.fibonacci_sequence(10))
    results = [
        ("Factorial (10!)", ok_f, note_f, "10! = 3,628,800"),
        ("Binomial Coefficient C(10, 4)", ok_c, note_c, "C(10, 4) = 210"),
        ("Binomial Expansion of (2x - 3y)^3", ok_e, note_e, expanded),
        ("Fibonacci Closed Form via rsolve() (Binet's Formula)", ok_r and all(c["matched"] for c in checks), note_r, "F(n) = " + closed),
    ]
    return {
        "available": True,
        "version": SYMPY_VERSION,
        "message": f"SymPy {SYMPY_VERSION} formal symbolic verification active.",
        "results": [{"name": a, "verified": b, "detail": c, "expression": d} for a, b, c, d in results],
    }
