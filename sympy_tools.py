# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: sympy_tools.py - Formal verification using SymPy symbolic mathematics

SYMPY_AVAILABLE = False
SYMPY_VERSION = "Not installed"

try:
    import sympy
    from sympy import factorial as sym_factorial
    from sympy import binomial as sym_binomial
    from sympy import symbols, expand, simplify, Function, rsolve
    SYMPY_AVAILABLE = True
    SYMPY_VERSION = str(sympy.__version__)
except ImportError:
    SYMPY_AVAILABLE = False
    SYMPY_VERSION = "Not installed"


def is_sympy_available():
    """Returns True if SymPy is installed and successfully imported."""
    return SYMPY_AVAILABLE


def get_sympy_version():
    """Returns the detected version string of SymPy or 'Not installed'."""
    return SYMPY_VERSION


def get_install_instructions():
    """Returns terminal instructions for installing SymPy."""
    return "SymPy is not installed. To enable formal symbolic verification, run: pip install sympy"


def sympy_verify_factorial(n, my_result):
    """Cross-verifies my factorial result against SymPy's factorial function.
    
    Returns a tuple: (is_verified, sympy_value, note_string).
    """
    if not SYMPY_AVAILABLE:
        return (False, None, get_install_instructions())
    
    try:
        sym_val = int(sym_factorial(n))
        is_match = (sym_val == my_result)
        if is_match:
            note = "SymPy factorial(" + str(n) + ") = " + str(sym_val) + " [VERIFIED MATCH]"
        else:
            note = "Mismatch: my result = " + str(my_result) + ", SymPy = " + str(sym_val)
        return (is_match, sym_val, note)
    except Exception as e:
        return (False, None, "SymPy verification error: " + str(e))


def sympy_verify_combination(n, r, my_result):
    """Cross-verifies my combinations result against SymPy's binomial function.
    
    Returns a tuple: (is_verified, sympy_value, note_string).
    """
    if not SYMPY_AVAILABLE:
        return (False, None, get_install_instructions())
    
    try:
        sym_val = int(sym_binomial(n, r))
        is_match = (sym_val == my_result)
        if is_match:
            note = "SymPy binomial(" + str(n) + ", " + str(r) + ") = " + str(sym_val) + " [VERIFIED MATCH]"
        else:
            note = "Mismatch: my result = " + str(my_result) + ", SymPy = " + str(sym_val)
        return (is_match, sym_val, note)
    except Exception as e:
        return (False, None, "SymPy verification error: " + str(e))


def sympy_verify_expansion(n, a, b, my_terms):
    """Verifies my binomial expansion terms against SymPy's expand((a*x + b*y)^n).
    
    Constructs the expression purely from integer symbols and checks if the difference
    simplifies to zero. Does NOT evaluate or parse arbitrary user strings.
    
    Returns a tuple: (is_verified, sympy_expanded_str, note_string).
    """
    if not SYMPY_AVAILABLE:
        return (False, "", get_install_instructions())
    
    try:
        x, y = symbols("x y")
        # Build my expression from calculated integer tuples (coeff, x_pow, y_pow)
        my_expr = 0
        for coeff, x_pow, y_pow in my_terms:
            term_sym = coeff * (x ** x_pow) * (y ** y_pow)
            my_expr = my_expr + term_sym
        
        # Build theoretical expression and expand formally
        theoretical_expr = (a * x + b * y) ** n
        expected_expanded = expand(theoretical_expr)
        
        # Verify difference simplifies exactly to integer 0
        difference = simplify(expected_expanded - my_expr)
        is_verified = (difference == 0)
        
        expected_str = str(expected_expanded)
        if is_verified:
            note = "SymPy expand((" + str(a) + "*x + " + str(b) + "*y)^" + str(n) + ") matches my expansion. Difference = 0 [VERIFIED MATCH]"
        else:
            note = "Expansion difference did not simplify to 0: " + str(difference)
        
        return (is_verified, expected_str, note)
    except Exception as e:
        return (False, "", "SymPy expansion error: " + str(e))


def sympy_closed_form_recurrence(rec_type, order_k, coefficients, initial_values, my_terms):
    """Computes symbolic closed-form solution using SymPy's rsolve for recurrences of order <= 2.
    
    Parameters:
      rec_type: 'fibonacci' or 'custom'
      order_k: Order of recurrence (1 or 2 supported for rsolve)
      coefficients: List of k integer coefficients [c1, c2]
      initial_values: Tuple of k integer initial values (a0, a1)
      my_terms: List of my generated numerical terms
      
    Returns a tuple: (success, closed_form_str, term_check_results, note_string)
    """
    if not SYMPY_AVAILABLE:
        return (False, "", [], get_install_instructions())
    
    if rec_type == "factorial":
        note = "Factorial recurrence a(n) = n*a(n-1) has variable coefficient n. Closed-form rsolve is restricted to constant-coefficient recurrences of order <= 2."
        return (False, "", [], note)
    
    if order_k > 2:
        note = "SymPy rsolve closed-form verification is restricted to recurrences of order <= 2."
        return (False, "", [], note)
    
    try:
        n = symbols("n", integer=True)
        f = Function("f")
        
        if rec_type == "fibonacci":
            rec_eq = sympy.Eq(f(n), f(n - 1) + f(n - 2))
            init_cond = {f(0): 0, f(1): 1}
        elif order_k == 1:
            c1 = coefficients[0]
            rec_eq = sympy.Eq(f(n), c1 * f(n - 1))
            init_cond = {f(0): initial_values[0]}
        elif order_k == 2:
            c1 = coefficients[0]
            c2 = coefficients[1]
            rec_eq = sympy.Eq(f(n), c1 * f(n - 1) + c2 * f(n - 2))
            init_cond = {f(0): initial_values[0], f(1): initial_values[1]}
        else:
            return (False, "", [], "Unsupported order for rsolve.")
        
        sol = rsolve(rec_eq, f(n), init_cond)
        if sol is None:
            return (False, "", [], "SymPy rsolve could not determine a closed-form solution.")
        
        closed_form_str = str(sol)
        
        # Verify first 10 generated terms (or up to len(my_terms)) using simplify (never float ==)
        check_count = min(10, len(my_terms))
        term_check_results = []
        all_matched = True
        
        for idx in range(check_count):
            subbed = sol.subs(n, idx)
            diff = simplify(subbed - my_terms[idx])
            matched = (diff == 0)
            if not matched:
                all_matched = False
            term_check_results.append({
                "n": idx,
                "my_term": my_terms[idx],
                "sympy_val": str(simplify(subbed)),
                "matched": matched
            })
        
        if all_matched:
            note = "All " + str(check_count) + " tested terms matched SymPy closed form exactly [VERIFIED MATCH]"
        else:
            note = "Some terms differed from SymPy closed form."
        
        return (True, closed_form_str, term_check_results, note)
    except Exception as e:
        return (False, "", [], "SymPy rsolve execution error: " + str(e))
